from __future__ import annotations
import winfix  # noqa: F401 - doit être importé en premier (correctif anti-blocage FFmpeg Windows)
import json, os, sys, threading, traceback, queue
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
import engine

APP = Path(__file__).resolve().parent
USER_DATA = Path(os.environ.get("APPDATA", Path.home())) / "Ty-Videos-Studio"
USER_DATA.mkdir(parents=True, exist_ok=True)
CONFIG = USER_DATA / "project.json"
OUTPUT = Path.home() / "Documents" / "Ty-Videos-Studio" / "output"
TEMP = USER_DATA / "temp"

MODE_SCENES = "scenes"
MODE_AUDIO = "audio"
SUBTITLE_LABELS = {
    "Aucun": engine.SUBTITLE_STYLE_NONE,
    "Classique (bas d'écran)": engine.SUBTITLE_STYLE_CLASSIC,
    "Dynamique (surligné)": engine.SUBTITLE_STYLE_DYNAMIC,
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SceneCard(ctk.CTkFrame):
    def __init__(self, parent, app, number, data=None):
        super().__init__(parent, corner_radius=16, fg_color=("#f4f6fb","#151923"), border_width=1,
                         border_color=("#dfe3ec","#242a38"))
        self.app=app; self.data=data or {}
        self.grid_columnconfigure(1,weight=1)
        self.title=ctk.CTkLabel(self,text=f"SCÈNE {number}",font=ctk.CTkFont(size=14,weight="bold"))
        self.title.grid(row=0,column=0,columnspan=2,sticky="w",padx=18,pady=(14,8))
        self.text=ctk.CTkTextbox(self,height=85,corner_radius=10)
        self.text.insert("1.0",self.data.get("text",""))
        self.text.grid(row=1,column=0,columnspan=2,sticky="ew",padx=18,pady=5)
        self.media=tk.StringVar(value=self.data.get("background",""))
        ctk.CTkLabel(self,text="Média de fond").grid(row=2,column=0,sticky="w",padx=18,pady=5)
        ctk.CTkEntry(self,textvariable=self.media,state="readonly").grid(row=2,column=1,sticky="ew",padx=(0,8),pady=5)
        ctk.CTkButton(self,text="Choisir",width=90,command=self.pick).grid(row=2,column=2,padx=(0,18),pady=5)
        ctk.CTkLabel(self,text="Texte").grid(row=3,column=0,sticky="w",padx=18,pady=5)
        self.mode=tk.StringVar(value=self.data.get("text_mode",engine.TEXT_MODE_NONE))
        self.modebox=ctk.CTkComboBox(self,values=["Sans texte","Texte complet","Sous-titres"],variable=tk.StringVar(),
                                     command=self.change_mode,width=170)
        labels={"none":"Sans texte","full":"Texte complet","subtitle":"Sous-titres"}
        self.modebox.set(labels.get(self.mode.get(),"Sans texte"))
        self.modebox.grid(row=3,column=1,sticky="w",pady=5)
        ctk.CTkButton(self,text="Dupliquer",width=100,fg_color="transparent",border_width=1,
                      command=self.duplicate).grid(row=3,column=2,padx=(0,18),pady=5)
        ctk.CTkButton(self,text="Supprimer",width=100,fg_color="#b33a3a",hover_color="#8e2d2d",
                      command=self.delete).grid(row=4,column=2,padx=(0,18),pady=(5,16))
    def change_mode(self,v):
        self.mode.set({"Sans texte":"none","Texte complet":"full","Sous-titres":"subtitle"}.get(v,"none"))
    def pick(self):
        p=filedialog.askopenfilename(title="Choisir un fond",filetypes=[
            ("Images et vidéos","*.png *.jpg *.jpeg *.webp *.bmp *.mp4 *.mov *.avi *.mkv *.webm"),
            ("Tous les fichiers","*.*")])
        if p:self.media.set(p)
    def get(self):
        return {"text":self.text.get("1.0","end").strip(),"background":self.media.get(),
                "text_mode":self.mode.get()}
    def delete(self): self.app.remove_scene(self)
    def duplicate(self): self.app.add_scene(self.get())

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ty-Videos-Studio")
        self.geometry("1180x820"); self.minsize(1000,700)
        self.scenes=[]
        self.log_queue=queue.Queue()
        self.ui_queue=queue.Queue()
        self.after(100, self.flush_log_queue)
        self.after(100, self.flush_ui_queue)
        self.protocol("WM_DELETE_WINDOW",self.close)
        self.build()
        self.load()
        if not self.scenes:
            self.add_scene(); self.add_scene()

    def build(self):
        self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(1,weight=1); self.grid_rowconfigure(2,weight=0)
        side=ctk.CTkFrame(self,width=235,corner_radius=0,fg_color=("#eef1f7","#0e1118")); side.grid(row=0,column=0,rowspan=2,sticky="nsew")
        ctk.CTkLabel(side,text="TY-VIDEOS",font=ctk.CTkFont(size=24,weight="bold")).pack(padx=24,pady=(28,2),anchor="w")
        ctk.CTkLabel(side,text="STUDIO",font=ctk.CTkFont(size=12,weight="bold"),text_color="#4ea1ff").pack(padx=25,anchor="w")
        self.status=ctk.CTkLabel(side,text="● Prêt",text_color="#5bd28c"); self.status.pack(padx=25,pady=(14,10),anchor="w")

        self.mode=tk.StringVar(value=MODE_SCENES)
        ctk.CTkLabel(side,text="MODE DE PRODUCTION",font=ctk.CTkFont(size=11,weight="bold"),text_color="#8b93a6").pack(padx=25,pady=(4,6),anchor="w")
        self.mode_switch=ctk.CTkSegmentedButton(side,values=["Scènes + texte","Voix off + photos"],command=self.set_mode)
        self.mode_switch.set("Scènes + texte")
        self.mode_switch.pack(padx=18,pady=(0,16),fill="x")

        ctk.CTkButton(side,text="＋  Nouvelle vidéo",command=self.new).pack(padx=18,pady=5,fill="x")
        ctk.CTkButton(side,text="💾  Enregistrer projet",fg_color="transparent",border_width=1,command=self.save).pack(padx=18,pady=5,fill="x")
        ctk.CTkButton(side,text="📂  Ouvrir projet",fg_color="transparent",border_width=1,command=self.open_project).pack(padx=18,pady=5,fill="x")
        ctk.CTkLabel(side,text="EXPORT",font=ctk.CTkFont(size=11,weight="bold"),text_color="#8b93a6").pack(padx=25,pady=(30,8),anchor="w")
        self.create_btn=ctk.CTkButton(side,text="🎬  Créer la vidéo",height=48,command=self.render)
        self.create_btn.pack(padx=18,pady=5,fill="x")
        ctk.CTkButton(side,text="↗  Ouvrir le dossier",fg_color="transparent",border_width=1,command=self.open_output).pack(padx=18,pady=5,fill="x")
        ctk.CTkLabel(side,text="Vidéo locale • Windows",text_color="#778095").pack(side="bottom",padx=18,pady=18,anchor="w")

        head=ctk.CTkFrame(self,height=70,corner_radius=0,fg_color=("#ffffff","#11151e")); head.grid(row=0,column=1,sticky="ew")
        ctk.CTkLabel(head,text="Créer une vidéo",font=ctk.CTkFont(size=22,weight="bold")).pack(side="left",padx=25,pady=20)
        self.format=tk.StringVar(value="9:16")
        ctk.CTkSegmentedButton(head,values=["9:16  Vertical","16:9  Horizontal"],command=self.set_format).pack(side="right",padx=25,pady=17)

        # main scroll
        self.scroll=ctk.CTkScrollableFrame(self,fg_color=("#f7f8fc","#0b0e14")); self.scroll.grid(row=1,column=1,sticky="nsew",padx=0,pady=0)
        self.scroll.grid_columnconfigure(0,weight=1)

        # --- Section "Scènes + texte" ---
        self.scenes_section=ctk.CTkFrame(self.scroll,fg_color="transparent")
        self.scenes_section.grid(row=0,column=0,sticky="ew")
        self.scenes_section.grid_columnconfigure(0,weight=1)
        bar=ctk.CTkFrame(self.scenes_section,fg_color="transparent"); bar.grid(row=0,column=0,sticky="ew",padx=24,pady=22)
        bar.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(bar,text="Scènes",font=ctk.CTkFont(size=19,weight="bold")).grid(row=0,column=0,sticky="w")
        ctk.CTkButton(bar,text="＋ Ajouter une scène",width=150,command=self.add_scene).grid(row=0,column=1)
        self.scene_area=ctk.CTkFrame(self.scenes_section,fg_color="transparent"); self.scene_area.grid(row=1,column=0,sticky="ew",padx=24)

        # --- Section "Voix off + photos/vidéos" ---
        self.audio_section=ctk.CTkFrame(self.scroll,fg_color="transparent")
        self.audio_section.grid(row=0,column=0,sticky="ew")
        self.audio_section.grid_columnconfigure(0,weight=1)

        vo=ctk.CTkFrame(self.audio_section,corner_radius=16,fg_color=("#f4f6fb","#151923"),border_width=1,
                        border_color=("#dfe3ec","#242a38"))
        vo.grid(row=0,column=0,sticky="ew",padx=24,pady=(22,14))
        vo.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(vo,text="Voix off à utiliser",font=ctk.CTkFont(size=15,weight="bold")).grid(row=0,column=0,columnspan=2,sticky="w",padx=18,pady=(16,8))
        self.voice_over_path=tk.StringVar()
        ctk.CTkEntry(vo,textvariable=self.voice_over_path,state="readonly").grid(row=1,column=0,sticky="ew",padx=(18,8),pady=(0,16))
        ctk.CTkButton(vo,text="Importer (mp3 / aac / wav)",width=200,command=self.pick_voice_over).grid(row=1,column=1,padx=(0,18),pady=(0,16))

        mb=ctk.CTkFrame(self.audio_section,corner_radius=16,fg_color=("#f4f6fb","#151923"),border_width=1,
                        border_color=("#dfe3ec","#242a38"))
        mb.grid(row=1,column=0,sticky="ew",padx=24,pady=(0,14))
        mb.grid_columnconfigure(0,weight=1)
        head2=ctk.CTkFrame(mb,fg_color="transparent"); head2.grid(row=0,column=0,sticky="ew",padx=18,pady=(16,8))
        head2.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(head2,text="Photos / vidéos de fond",font=ctk.CTkFont(size=15,weight="bold")).grid(row=0,column=0,sticky="w")
        ctk.CTkButton(head2,text="＋ Ajouter",width=110,command=self.add_media).grid(row=0,column=1)
        self.media_paths=[]
        self.media_list_box=tk.Listbox(mb,height=6,activestyle="none",bg="#0e1118",fg="#e8ebf2",
                                       selectbackground="#2c5fb3",highlightthickness=0,borderwidth=0)
        self.media_list_box.grid(row=1,column=0,sticky="ew",padx=18)
        mrow=ctk.CTkFrame(mb,fg_color="transparent"); mrow.grid(row=2,column=0,sticky="e",padx=18,pady=(8,16))
        ctk.CTkButton(mrow,text="↑",width=42,fg_color="transparent",border_width=1,command=lambda:self.move_media(-1)).pack(side="left",padx=3)
        ctk.CTkButton(mrow,text="↓",width=42,fg_color="transparent",border_width=1,command=lambda:self.move_media(1)).pack(side="left",padx=3)
        ctk.CTkButton(mrow,text="Retirer",width=90,fg_color="#b33a3a",hover_color="#8e2d2d",command=self.remove_media).pack(side="left",padx=(10,0))

        sb=ctk.CTkFrame(self.audio_section,corner_radius=16,fg_color=("#f4f6fb","#151923"),border_width=1,
                        border_color=("#dfe3ec","#242a38"))
        sb.grid(row=2,column=0,sticky="ew",padx=24)
        sb.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(sb,text="Sous-titres",font=ctk.CTkFont(size=15,weight="bold")).grid(row=0,column=0,columnspan=2,sticky="w",padx=18,pady=(16,8))
        self.subtitle_style=tk.StringVar(value="Classique (bas d'écran)")
        ctk.CTkComboBox(sb,values=list(SUBTITLE_LABELS),variable=self.subtitle_style,width=250).grid(row=1,column=0,sticky="w",padx=18,pady=(0,16))
        ctk.CTkLabel(sb,text="Générés automatiquement à partir de la voix off importée.",
                    text_color="#8b93a6",wraplength=420,justify="left").grid(row=1,column=1,sticky="w",padx=(0,18),pady=(0,16))

        self.audio_section.grid_remove()  # masqué par défaut (mode "Scènes + texte")

        # --- Réglages d'export (communs aux deux modes) ---
        self.opts=ctk.CTkFrame(self.scroll,corner_radius=16); self.opts.grid(row=1,column=0,sticky="ew",padx=24,pady=18)
        self.opts.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(self.opts,text="Réglages d'export",font=ctk.CTkFont(size=16,weight="bold")).grid(row=0,column=0,columnspan=3,sticky="w",padx=18,pady=(16,10))
        self.music=tk.StringVar(); self.voice=tk.StringVar(value="Féminine — Denise")
        self.zoom=tk.DoubleVar(value=0.06); self.output=tk.StringVar(value="ma_video.mp4")
        ctk.CTkLabel(self.opts,text="Musique").grid(row=1,column=0,sticky="w",padx=18,pady=7)
        ctk.CTkEntry(self.opts,textvariable=self.music).grid(row=1,column=1,sticky="ew",pady=7)
        ctk.CTkButton(self.opts,text="Choisir",width=80,command=self.pick_music).grid(row=1,column=2,padx=18)
        self.voice_label=ctk.CTkLabel(self.opts,text="Voix off")
        self.voice_label.grid(row=2,column=0,sticky="w",padx=18,pady=7)
        self.voice_combo=ctk.CTkComboBox(self.opts,values=list(engine.VOICES),variable=self.voice)
        self.voice_combo.grid(row=2,column=1,sticky="w",pady=7)
        ctk.CTkLabel(self.opts,text="Zoom images").grid(row=3,column=0,sticky="w",padx=18,pady=7)
        ctk.CTkSlider(self.opts,from_=0,to=.15,number_of_steps=15,variable=self.zoom,width=300).grid(row=3,column=1,sticky="w",pady=7)
        ctk.CTkLabel(self.opts,textvariable=self.zoom).grid(row=3,column=2,padx=18)
        ctk.CTkLabel(self.opts,text="Nom du fichier").grid(row=4,column=0,sticky="w",padx=18,pady=(7,18))
        ctk.CTkEntry(self.opts,textvariable=self.output).grid(row=4,column=1,sticky="w",pady=(7,18))

        # Fixed production console: always visible at the bottom of the window,
        # independently from the scenes scroll area.
        bottom=ctk.CTkFrame(self,corner_radius=0,fg_color=("#eef1f7","#11151e"),border_width=1,border_color=("#dfe3ec","#242a38"))
        bottom.grid(row=2,column=1,sticky="ew")
        bottom.grid_columnconfigure(0,weight=1)
        self.progress=ctk.CTkProgressBar(bottom,height=8); self.progress.set(0); self.progress.grid(row=0,column=0,sticky="ew",padx=18,pady=(10,5))
        self.log=ctk.CTkTextbox(bottom,height=135,corner_radius=8); self.log.grid(row=1,column=0,sticky="ew",padx=18,pady=(2,10))
        self.log.insert("end","Console de production — en attente d'une vidéo.\n")

    # --- Mode switch ---
    def set_mode(self,v):
        audio = v.startswith("Voix off")
        self.mode.set(MODE_AUDIO if audio else MODE_SCENES)
        if audio:
            self.scenes_section.grid_remove()
            self.audio_section.grid()
            self.voice_label.grid_remove(); self.voice_combo.grid_remove()
            self.create_btn.configure(text="🎙️  Créer la vidéo")
        else:
            self.audio_section.grid_remove()
            self.scenes_section.grid()
            self.voice_label.grid(); self.voice_combo.grid()
            self.create_btn.configure(text="🎬  Créer la vidéo")

    def set_format(self,v):
        self.format.set("9:16" if v.startswith("9:16") else "16:9")

    # --- Scènes ---
    def add_scene(self,data=None):
        card=SceneCard(self.scene_area,self,len(self.scenes)+1,data); card.pack(fill="x",pady=7)
        self.scenes.append(card); self.renumber()
    def remove_scene(self,card):
        if len(self.scenes)<=1:return messagebox.showwarning("Ty-Videos-Studio","Il faut garder au moins une scène.")
        card.destroy(); self.scenes.remove(card); self.renumber()
    def renumber(self):
        for i,c in enumerate(self.scenes,1): c.title.configure(text=f"SCÈNE {i}")

    # --- Mode "Voix off + photos/vidéos" ---
    def pick_voice_over(self):
        p=filedialog.askopenfilename(title="Choisir une voix off",
                                     filetypes=[("Audio","*.mp3 *.aac *.wav *.m4a *.ogg"),("Tous","*.*")])
        if p:self.voice_over_path.set(p)
    def add_media(self):
        paths=filedialog.askopenfilenames(title="Ajouter des photos/vidéos",filetypes=[
            ("Images et vidéos","*.png *.jpg *.jpeg *.webp *.bmp *.mp4 *.mov *.avi *.mkv *.webm"),
            ("Tous les fichiers","*.*")])
        for p in paths:
            self.media_paths.append(p)
            self.media_list_box.insert("end",Path(p).name)
    def remove_media(self):
        sel=list(self.media_list_box.curselection())
        for i in reversed(sel):
            self.media_list_box.delete(i); del self.media_paths[i]
    def move_media(self,direction):
        sel=self.media_list_box.curselection()
        if not sel:return
        i=sel[0]; j=i+direction
        if j<0 or j>=len(self.media_paths):return
        self.media_paths[i],self.media_paths[j]=self.media_paths[j],self.media_paths[i]
        name_i=self.media_list_box.get(i); name_j=self.media_list_box.get(j)
        self.media_list_box.delete(i);self.media_list_box.insert(i,name_j)
        self.media_list_box.delete(j);self.media_list_box.insert(j,name_i)
        self.media_list_box.selection_clear(0,"end"); self.media_list_box.selection_set(j)
    def subtitle_style_code(self):
        return SUBTITLE_LABELS.get(self.subtitle_style.get(), engine.SUBTITLE_STYLE_CLASSIC)

    def pick_music(self):
        p=filedialog.askopenfilename(title="Choisir une musique",filetypes=[("Audio","*.mp3 *.wav *.m4a *.ogg"),("Tous","*.*")])
        if p:self.music.set(p)

    def write_log(self,s):
        # Only the Tk main thread updates widgets.
        self.log_queue.put(str(s))

    def flush_log_queue(self):
        try:
            while True:
                msg=self.log_queue.get_nowait()
                self.log.insert("end",msg+"\n")
                self.log.see("end")
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100,self.flush_log_queue)

    def post_ui(self, kind, value=None):
        self.ui_queue.put((kind, value))

    def flush_ui_queue(self):
        try:
            while True:
                kind,value=self.ui_queue.get_nowait()
                if kind=="success": self.render_success(value)
                elif kind=="error": self.render_error(value)
                elif kind=="finish": self.finish()
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100,self.flush_ui_queue)

    # --- Rendu : dispatch selon le mode ---
    def render(self):
        if self.mode.get()==MODE_AUDIO:
            self.render_audio()
        else:
            self.render_scenes()

    def collect(self):
        scenes=[s.get() for s in self.scenes]
        for i,s in enumerate(scenes,1):
            if not s["text"]: raise ValueError(f"Scène {i}: texte vide.")
            if not s["background"] or not Path(s["background"]).exists(): raise ValueError(f"Scène {i}: fond invalide.")
            engine.check_media_format(s["background"],self.format.get())
        return scenes

    def prepare_output(self):
        OUTPUT.mkdir(parents=True,exist_ok=True); TEMP.mkdir(parents=True,exist_ok=True)
        name=self.output.get().strip() or "ma_video.mp4"
        if not name.lower().endswith(".mp4"): name += ".mp4"
        return OUTPUT/name

    def start_production(self, header_lines, work):
        self.status.configure(text="● Production en cours…",text_color="#ffbf4a")
        self.progress.configure(mode="indeterminate"); self.progress.start(12)
        self.log.delete("1.0","end")
        self.write_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for line in header_lines: self.write_log(line)
        self.write_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        self.create_btn.configure(state="disabled")
        threading.Thread(target=work,daemon=True).start()

    def render_scenes(self):
        try:
            scenes=self.collect()
        except Exception as e:
            messagebox.showerror("Vérification",str(e)); return
        out=self.prepare_output()
        try:
            voice,pitch=engine.VOICES[self.voice.get()]
            settings={"format":self.format.get(),"voice":voice,"pitch":pitch,"zoom":float(self.zoom.get()),
                      "music":self.music.get().strip(),"music_volume":.10,"fps":24,
                      "project_dir":str(APP),"temp_dir":str(TEMP)}
        except Exception as e:
            messagebox.showerror("Réglages",str(e)); return
        header=["TY-VIDEOS-STUDIO — DÉMARRAGE",
                f"Format : {settings['format']}",
                f"Scènes : {len(scenes)}",
                f"Sortie : {out}",
                "La génération peut prendre plusieurs minutes.",
                "La voix off nécessite une connexion Internet."]
        def work():
            try:
                result=engine.render_project(scenes,settings,out,self.write_log)
                self.post_ui("success", result)
            except Exception as e:
                self.write_log("ERREUR DE PRODUCTION : "+str(e))
                self.write_log(traceback.format_exc())
                self.post_ui("error", str(e))
            finally:
                self.post_ui("finish")
        self.start_production(header, work)

    def collect_audio(self):
        voice=self.voice_over_path.get().strip()
        if not voice or not Path(voice).exists():
            raise ValueError("Choisis un fichier de voix off (mp3, aac ou wav).")
        if not self.media_paths:
            raise ValueError("Ajoute au moins une photo ou vidéo de fond.")
        for m in self.media_paths:
            if not Path(m).exists():
                raise ValueError(f"Média introuvable : {m}")
        return voice, list(self.media_paths)

    def render_audio(self):
        try:
            voice,media=self.collect_audio()
        except Exception as e:
            messagebox.showerror("Vérification",str(e)); return
        out=self.prepare_output()
        settings={"format":self.format.get(),"zoom":float(self.zoom.get()),
                  "music":self.music.get().strip(),"music_volume":.10,"fps":24,
                  "project_dir":str(APP),"temp_dir":str(TEMP)}
        style=self.subtitle_style_code()
        header=["TY-VIDEOS-STUDIO — VOIX OFF + PHOTOS/VIDÉOS",
                f"Format : {settings['format']}",
                f"Médias de fond : {len(media)}",
                f"Sortie : {out}",
                "La transcription des sous-titres peut nécessiter Internet la première fois."]
        def work():
            try:
                result=engine.render_from_audio(media,voice,style,settings,out,self.write_log)
                self.post_ui("success", result)
            except Exception as e:
                self.write_log("ERREUR DE PRODUCTION : "+str(e))
                self.write_log(traceback.format_exc())
                self.post_ui("error", str(e))
            finally:
                self.post_ui("finish")
        self.start_production(header, work)

    def render_success(self,result):
        if not Path(result).exists() or Path(result).stat().st_size < 10000:
            self.render_error("Le moteur a terminé sans produire un fichier MP4 valide.")
            return
        self.status.configure(text="● Vidéo créée",text_color="#5bd28c")
        messagebox.showinfo("Ty-Videos-Studio",f"La vidéo a été créée avec succès.\n\nFichier :\n{result}")

    def render_error(self,msg):
        self.status.configure(text="● Erreur",text_color="#ff6b6b")
        messagebox.showerror("Erreur de production","La production n'a pas pu se terminer.\n\n"+msg+"\n\nConsulte le journal en bas de la fenêtre pour le détail.")

    def finish(self):
        self.progress.stop(); self.progress.configure(mode="determinate"); self.progress.set(1)
        self.create_btn.configure(state="normal")
        if self.status.cget("text")=="● Production en cours…":
            self.status.configure(text="● Prêt",text_color="#5bd28c")

    def save(self):
        data={"format":self.format.get(),"music":self.music.get(),"voice":self.voice.get(),"zoom":self.zoom.get(),"output":self.output.get(),
              "scenes":[s.get() for s in self.scenes],
              "mode":self.mode.get(),
              "voice_over_path":self.voice_over_path.get(),
              "media_paths":list(self.media_paths),
              "subtitle_style":self.subtitle_style.get()}
        CONFIG.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        self.write_log("Projet enregistré dans les données utilisateur.")

    def _load_media(self,paths):
        self.media_list_box.delete(0,"end"); self.media_paths=[]
        for m in paths:
            self.media_paths.append(m); self.media_list_box.insert("end",Path(m).name)

    def load(self):
        if not CONFIG.exists():return
        try:
            d=json.loads(CONFIG.read_text(encoding="utf-8"))
            self.set_format("9:16  Vertical" if d.get("format","9:16")=="9:16" else "16:9  Horizontal")
            self.music.set(d.get("music","")); self.voice.set(d.get("voice","Féminine — Denise"))
            self.zoom.set(float(d.get("zoom",0.06))); self.output.set(d.get("output","ma_video.mp4"))
            for s in d.get("scenes",[]): self.add_scene(s)
            self.voice_over_path.set(d.get("voice_over_path",""))
            self._load_media(d.get("media_paths",[]))
            self.subtitle_style.set(d.get("subtitle_style","Classique (bas d'écran)"))
            mode_label="Voix off + photos" if d.get("mode",MODE_SCENES)==MODE_AUDIO else "Scènes + texte"
            self.mode_switch.set(mode_label); self.set_mode(mode_label)
        except Exception: pass

    def open_project(self):
        p=filedialog.askopenfilename(title="Ouvrir un projet",filetypes=[("Projet Ty-Videos-Studio","*.json")])
        if not p:return
        try:
            d=json.loads(Path(p).read_text(encoding="utf-8"))
            for s in self.scenes:s.destroy()
            self.scenes=[]
            self.set_format("9:16  Vertical" if d.get("format","9:16")=="9:16" else "16:9  Horizontal")
            self.music.set(d.get("music","")); self.voice.set(d.get("voice","Féminine — Denise")); self.zoom.set(float(d.get("zoom",0.06))); self.output.set(d.get("output","ma_video.mp4"))
            for s in d.get("scenes",[]):self.add_scene(s)
            self.voice_over_path.set(d.get("voice_over_path",""))
            self._load_media(d.get("media_paths",[]))
            self.subtitle_style.set(d.get("subtitle_style","Classique (bas d'écran)"))
            mode_label="Voix off + photos" if d.get("mode",MODE_SCENES)==MODE_AUDIO else "Scènes + texte"
            self.mode_switch.set(mode_label); self.set_mode(mode_label)
        except Exception as e:messagebox.showerror("Projet",str(e))

    def new(self):
        for s in self.scenes:s.destroy()
        self.scenes=[]; self.add_scene(); self.add_scene()
        self.music.set("");self.output.set("ma_video.mp4")
        self.voice_over_path.set(""); self._load_media([])
        self.subtitle_style.set("Classique (bas d'écran)")
        self.mode_switch.set("Scènes + texte"); self.set_mode("Scènes + texte")

    def open_output(self):
        OUTPUT.mkdir(exist_ok=True); os.startfile(str(OUTPUT))

    def close(self):
        try:self.save()
        except:pass
        self.destroy()

if __name__=="__main__":
    App().mainloop()
