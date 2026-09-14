"""
VideoForge Studio - moteur de rendu vidéo.
Inspiré du générateur fourni : scènes image/vidéo, 9:16/16:9,
3 modes texte, Ken Burns, voix off et musique de fond.
"""

from __future__ import annotations
import asyncio, os, subprocess, textwrap, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Force MoviePy to use the FFmpeg executable bundled by imageio-ffmpeg.
try:
    import imageio_ffmpeg
    _ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if _ffmpeg and Path(_ffmpeg).exists():
        os.environ["IMAGEIO_FFMPEG_EXE"] = _ffmpeg
except Exception:
    pass

from moviepy import (
    AudioFileClip, ImageClip, VideoFileClip, CompositeAudioClip,
    CompositeVideoClip, concatenate_videoclips
)
from moviepy.video.fx import Loop as VideoLoop

def get_ffmpeg_exe():
    """Return bundled FFmpeg, or a system FFmpeg as fallback."""
    try:
        import imageio_ffmpeg
        exe=imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists(): return exe
    except Exception:
        pass
    exe=shutil.which("ffmpeg")
    if exe: return exe
    raise RenderError("FFmpeg est introuvable. Cette version doit être recompilée avec FFmpeg inclus.")


VIDEO_FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
BASE_DIR = Path(__file__).resolve().parent
VIDEO_EXTENSIONS = {".mp4",".mov",".avi",".mkv",".webm",".m4v"}
TEXT_MODE_NONE, TEXT_MODE_FULL, TEXT_MODE_SUBTITLE = "none", "full", "subtitle"

VOICES = {
    "Féminine — Denise": ("fr-FR-DeniseNeural", "+0Hz"),
    "Masculine — Henri": ("fr-FR-HenriNeural", "+0Hz"),
    "Masculine — Remy": ("fr-FR-RemyMultilingualNeural", "+0Hz"),
    "Masculine — Grave": ("fr-FR-HenriNeural", "-25Hz"),
}

class RenderError(Exception): pass
class FormatMismatchError(RenderError): pass

def is_video_file(path): return Path(path).suffix.lower() in VIDEO_EXTENSIONS

def media_size(path):
    if is_video_file(path):
        clip = VideoFileClip(str(path))
        try: return clip.size
        finally: clip.close()
    with Image.open(path) as im: return im.size

def check_media_format(path, fmt):
    w, h = media_size(path)
    tw, th = VIDEO_FORMATS[fmt]
    if w != h and (h > w) != (th > tw):
        raise FormatMismatchError(
            f"Le média « {Path(path).name} » n'a pas la même orientation que {fmt}."
        )

def cover_image(path, size):
    W, H = size
    im = Image.open(path).convert("RGB")
    ratio = im.width / im.height
    target = W / H
    if ratio > target:
        nh, nw = H, int(H * ratio)
    else:
        nw, nh = W, int(W / ratio)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left, top = (nw-W)//2, (nh-H)//2
    return im.crop((left, top, left+W, top+H))

def cover_video(path, size, duration):
    W, H = size
    clip = VideoFileClip(str(path)).without_audio()
    ratio, target = clip.w/clip.h, W/H
    if ratio > target: clip = clip.resized(height=H)
    else: clip = clip.resized(width=W)
    clip = clip.cropped(x_center=clip.w/2, y_center=clip.h/2, width=W, height=H)
    if clip.duration < duration:
        clip = clip.with_effects([VideoLoop(duration=duration)])
    else:
        clip = clip.subclipped(0, duration)
    return clip.with_duration(duration)

def font_for(size):
    candidates = [
        BASE_DIR / "assets/fonts/Montserrat-Bold.ttf",
        BASE_DIR / "assets/fonts/DejaVuSans-Bold.ttf",
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()

def zoom_clip(clip, ratio):
    if not ratio or ratio <= 0: return clip
    duration, w, h = clip.duration, clip.w, clip.h
    def effect(get_frame, t):
        frame = get_frame(t)
        scale = 1 + ratio * (t / duration if duration else 0)
        nw, nh = int(w*scale), int(h*scale)
        resized = Image.fromarray(frame).resize((nw,nh), Image.Resampling.LANCZOS)
        return np.array(resized.crop(((nw-w)//2,(nh-h)//2,(nw+w)//2,(nh+h)//2)))
    return clip.transform(effect)

def full_overlay(text, size, reveal=None):
    W,H=size
    font=font_for(max(42, int(W*0.065)))
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    words=textwrap.wrap(text, width=25 if W < H else 45)
    if reveal is not None:
        chars=max(0,reveal); shown=[]; left=chars
        for line in words:
            n=min(len(line),left); shown.append(line[:n]); left-=len(line)
        words=shown
    boxes=[]
    for line in words:
        bb=d.textbbox((0,0),line,font=font); boxes.append((bb[2]-bb[0],bb[3]-bb[1]))
    total=sum(h for _,h in boxes)+18*max(0,len(boxes)-1)
    maxw=max([w for w,_ in boxes], default=0)
    y=(H-total)//2
    pad=42
    d.rounded_rectangle(((W-maxw)//2-pad,y-pad,(W+maxw)//2+pad,y+total+pad),
                        radius=28,fill=(8,12,20,175))
    yy=y
    for line,(lw,lh) in zip(words,boxes):
        if line:
            x=(W-lw)//2
            d.text((x+3,yy+3),line,font=font,fill=(0,0,0,230))
            d.text((x,yy),line,font=font,fill=(255,255,255,255))
        yy += lh+18
    return layer

def subtitle_overlay(text, size):
    W,H=size
    font=font_for(max(34,int(W*0.042)))
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    words=text.split(); lines=[]; cur=""
    for word in words:
        test=(cur+" "+word).strip()
        if d.textbbox((0,0),test,font=font)[2] <= W*0.78 or not cur: cur=test
        else: lines.append(cur); cur=word
    if cur: lines.append(cur)
    lines=lines[:2]
    dims=[d.textbbox((0,0),x,font=font) for x in lines]
    widths=[b[2]-b[0] for b in dims]; heights=[b[3]-b[1] for b in dims]
    total=sum(heights)+10*(len(lines)-1); y=H-int(H*.18)-total
    pad=22; mw=max(widths or [0])
    d.rounded_rectangle(((W-mw)//2-pad,y-pad,(W+mw)//2+pad,y+total+pad),
                        radius=18,fill=(0,0,0,185))
    for line,w,h in zip(lines,widths,heights):
        x=(W-w)//2
        d.text((x+2,y+2),line,font=font,fill=(0,0,0,255))
        d.text((x,y),line,font=font,fill=(255,255,255,255))
        y+=h+10
    return layer

async def tts(text, out, voice_name, pitch):
    import edge_tts
    # Edge TTS is network-based. Give it a finite timeout so the application
    # cannot remain indefinitely in "Production en cours" when the network
    # is unavailable.
    communicate = edge_tts.Communicate(text, voice_name, pitch=pitch)
    await asyncio.wait_for(communicate.save(str(out)), timeout=90)

def _render_scene(scene, idx, settings, temp_dir, log):
    fmt=settings["format"]; size=VIDEO_FORMATS[fmt]
    text=scene["text"].strip(); bg=Path(scene["background"])
    if not text: raise RenderError(f"Scène {idx}: texte vide.")
    if not bg.exists(): raise RenderError(f"Scène {idx}: média introuvable: {bg}")
    check_media_format(bg,fmt)
    audio=temp_dir/f"voice_{idx}.mp3"
    log(f"Scène {idx}: génération de la voix off…")
    asyncio.run(tts(text,audio,settings["voice"],settings["pitch"]))
    if not audio.exists() or audio.stat().st_size == 0:
        raise RenderError(f"Scène {idx}: la voix off n’a pas été générée.")
    log(f"Scène {idx}: voix off terminée — fichier audio OK.")
    voice=AudioFileClip(str(audio)); dur=voice.duration
    pause=.55; total=dur+pause
    mode=scene.get("text_mode",TEXT_MODE_NONE)
    if is_video_file(bg):
        base=cover_video(bg,size,total).with_fps(settings["fps"])
        if mode==TEXT_MODE_NONE: visual=base
        elif mode==TEXT_MODE_FULL:
            frames=[]; n=max(5,int(.45*settings["fps"]))
            font=font_for(max(42,int(size[0]*.065))); dummy=ImageDraw.Draw(Image.new("RGB",(1,1)))
            totalchars=len(text)
            for i in range(1,n+1):
                layer=full_overlay(text,size,round(totalchars*i/n))
                p=temp_dir/f"ov_{idx}_{i}.png"; layer.save(p)
                frames.append(ImageClip(str(p)).with_duration(.45/n))
            layer=full_overlay(text,size,totalchars); p=temp_dir/f"ov_{idx}_full.png"; layer.save(p)
            frames.append(ImageClip(str(p)).with_duration(dur+pause))
            track=concatenate_videoclips(frames,method="compose").with_fps(settings["fps"])
            visual=CompositeVideoClip([base,track],size=size)
            voice=voice.with_start(.45)
        else:
            groups=[" ".join(text.split()[i:i+6]) for i in range(0,len(text.split()),6)] or [""]
            clips=[]
            for g in groups:
                p=temp_dir/f"sub_{idx}_{len(clips)}.png"; subtitle_overlay(g,size).save(p)
                clips.append(ImageClip(str(p)).with_duration(total*len(g.split())/max(1,len(text.split()))))
            track=concatenate_videoclips(clips,method="compose").with_fps(settings["fps"])
            visual=CompositeVideoClip([base,track],size=size)
    else:
        bgim=cover_image(bg,size)
        if mode==TEXT_MODE_SUBTITLE:
            groups=[" ".join(text.split()[i:i+6]) for i in range(0,len(text.split()),6)] or [""]
            clips=[]
            for g in groups:
                frame=Image.alpha_composite(bgim.convert("RGBA"),subtitle_overlay(g,size)).convert("RGB")
                p=temp_dir/f"sub_{idx}_{len(clips)}.png"; frame.save(p)
                clips.append(ImageClip(str(p)).with_duration(total*len(g.split())/max(1,len(text.split()))))
            visual=zoom_clip(concatenate_videoclips(clips,method="compose").with_fps(settings["fps"]),settings["zoom"])
        elif mode==TEXT_MODE_FULL:
            n=max(5,int(.45*settings["fps"])); frames=[]; totalchars=len(text)
            for i in range(1,n+1):
                frame=Image.alpha_composite(bgim.convert("RGBA"),full_overlay(text,size,round(totalchars*i/n))).convert("RGB")
                p=temp_dir/f"full_{idx}_{i}.png"; frame.save(p)
                frames.append(ImageClip(str(p)).with_duration(.45/n))
            frame=Image.alpha_composite(bgim.convert("RGBA"),full_overlay(text,size,totalchars)).convert("RGB")
            p=temp_dir/f"full_{idx}_final.png"; frame.save(p)
            frames.append(ImageClip(str(p)).with_duration(dur+pause))
            visual=zoom_clip(concatenate_videoclips(frames,method="compose").with_fps(settings["fps"]),settings["zoom"])
            voice=voice.with_start(.45)
        else:
            p=temp_dir/f"bg_{idx}.png"; bgim.save(p)
            visual=zoom_clip(ImageClip(str(p)).with_duration(total).with_fps(settings["fps"]),settings["zoom"])
    return visual.with_audio(CompositeAudioClip([voice]))

def render_project(scenes, settings, output_path, log=lambda x:None):
    log("Vérification du moteur vidéo…")
    if not scenes:
        raise RenderError("Aucune scène à produire.")
    ffmpeg = get_ffmpeg_exe()
    log(f"FFmpeg : {Path(ffmpeg).name}")
    root=Path(settings.get("project_dir",".")).resolve()
    temp=Path(settings.get("temp_dir",root/"temp")); temp.mkdir(parents=True,exist_ok=True)
    out=Path(output_path); out.parent.mkdir(parents=True,exist_ok=True)
    files=[]
    for i,s in enumerate(scenes,1):
        log(f"Scène {i}/{len(scenes)} — rendu…")
        clip=_render_scene(s,i,settings,temp,log)
        fp=temp/f"scene_{i:03d}.mp4"
        try:
            log(f"Scène {i}: encodage MP4 en cours…")
            clip.write_videofile(str(fp),fps=settings["fps"],codec="libx264",audio_codec="aac",
                                 logger=None,threads=2,preset="medium")
        finally:
            clip.close()
        if not fp.exists() or fp.stat().st_size < 10000:
            raise RenderError(f"Scène {i}: le fichier vidéo n'a pas été généré correctement.")
        files.append(fp)
        log(f"✓ Scène {i} terminée : {fp.name}")
    concat=temp/"concat.txt"
    concat.write_text("\n".join(f"file '{f.as_posix()}'" for f in files),encoding="utf-8")
    raw=temp/"assembled.mp4"
    cmd=[ffmpeg,"-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(raw)]
    subprocess.run(cmd,check=True,capture_output=True,text=True)
    music=settings.get("music","")
    if music and Path(music).exists():
        log("Ajout de la musique de fond…")
        cmd=[ffmpeg,"-y","-i",str(raw),"-stream_loop","-1","-i",music,
             "-filter_complex",f"[1:a]volume={settings.get('music_volume',.10)}[m];[0:a][m]amix=inputs=2:duration=first[a]",
             "-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-shortest",str(out)]
        r=subprocess.run(cmd,capture_output=True,text=True)
        if r.returncode!=0:
            log("Musique : impossible de mixer la musique, conservation de la vidéo sans musique.")
            log(r.stderr[-1200:])
            raw.replace(out)
    else:
        raw.replace(out)
    for f in files:
        try:f.unlink()
        except:pass
    try:concat.unlink()
    except:pass
    log(f"VIDÉO CRÉÉE : {out}")
    return out
