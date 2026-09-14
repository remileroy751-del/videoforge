from __future__ import annotations
import json, os, sys, threading, traceback
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
        self.protocol("WM_DELETE_WINDOW",self.close)
        self.build()
        self.load()
        if not self.scenes:
            self.add_scene(); self.add_scene()
    def build(self):
        self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(1,weight=1)
        side=ctk.CTkFrame(self,width=235,corner_radius=0,fg_color=("#eef1f7","#0e1118")); side.grid(row=0,column=0,rowspan=2,sticky="nsew")
        ctk.CTkLabel(side,text="TY-VIDEOS",font=ctk.CTkFont(size=24,weight="bold")).pack(padx=24,pady=(28,2),anchor="w")
        ctk.CTkLabel(side,text="STUDIO",font=ctk.CTkFont(size=12,weight="bold"),text_color="#4ea1ff").pack(padx=25,anchor="w")
        self.status=ctk.CTkLabel(side,text="● Prêt",text_color="#5bd28c"); self.status.pack(padx=25,pady=24,anchor="w")
        ctk.CTkButton(side,text="＋  Nouvelle vidéo",command=self.new).pack(padx=18,pady=5,fill="x")
        ctk.CTkButton(side,text="💾  Enregistrer projet",fg_color="transparent",border_width=1,command=self.save).pack(padx=18,pady=5,fill="x")
        ctk.CTkButton(side,text="📂  Ouvrir projet",fg_color="transparent",border_width=1,command=self.open_project).pack(padx=18,pady=5,fill="x")
        ctk.CTkLabel(side,text="EXPORT",font=ctk.CTkFont(size=11,weight="bold"),text_color="#8b93a6").pack(padx=25,pady=(30,8),anchor="w")
        ctk.CTkButton(side,text="🎬  Créer la vidéo",height=48,command=self.render).pack(padx=18,pady=5,fill="x")
        ctk.CTkButton(side,text="↗  Ouvrir le dossier",fg_color="transparent",border_width=1,command=self.open_output).pack(padx=18,pady=5,fill="x")
        ctk.CTkLabel(side,text="Vidéo locale • Windows",text_color="#778095").pack(side="bottom",padx=18,pady=18,anchor="w")
        head=ctk.CTkFrame(self,height=70,corner_radius=0,fg_color=("#ffffff","#11151e")); head.grid(row=0,column=1,sticky="ew")
        ctk.CTkLabel(head,text="Créer une vidéo",font=ctk.CTkFont(size=22,weight="bold")).pack(side="left",padx=25,pady=20)
        self.format=tk.StringVar(value="9:16")
        ctk.CTkSegmentedButton(head,values=["9:16  Vertical","16:9  Horizontal"],command=self.set_format).pack(side="right",padx=25,pady=17)
        # main scroll
        self.scroll=ctk.CTkScrollableFrame(self,fg_color=("#f7f8fc","#0b0e14")); self.scroll.grid(row=1,column=1,sticky="nsew",padx=0,pady=0)
        self.scroll.grid_columnconfigure(0,weight=1)
        bar=ctk.CTkFrame(self.scroll,fg_color="transparent"); bar.grid(row=0,column=0,sticky="ew",padx=24,pady=22)
        bar.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(bar,text="Scènes",font=ctk.CTkFont(size=19,weight="bold")).grid(row=0,column=0,sticky="w")
        ctk.CTkButton(bar,text="＋ Ajouter une scène",width=150,command=self.add_scene).grid(row=0,column=1)
        self.scene_area=ctk.CTkFrame(self.scroll,fg_color="transparent"); self.scene_area.grid(row=1,column=0,sticky="ew",padx=24)
        self.opts=ctk.CTkFrame(self.scroll,corner_radius=16); self.opts.grid(row=2,column=0,sticky="ew",padx=24,pady=18)
        self.opts.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(self.opts,text="Réglages d'export",font=ctk.CTkFont(size=16,weight="bold")).grid(row=0,column=0,columnspan=3,sticky="w",padx=18,pady=(16,10))
        self.music=tk.StringVar(); self.voice=tk.StringVar(value="Féminine — Denise")
        self.zoom=tk.DoubleVar(value=0.06); self.output=tk.StringVar(value="ma_video.mp4")
        ctk.CTkLabel(self.opts,text="Musique").grid(row=1,column=0,sticky="w",padx=18,pady=7)
        ctk.CTkEntry(self.opts,textvariable=self.music).grid(row=1,column=1,sticky="ew",pady=7)
        ctk.CTkButton(self.opts,text="Choisir",width=80,command=self.pick_music).grid(row=1,column=2,padx=18)
        ctk.CTkLabel(self.opts,text="Voix off").grid(row=2,column=0,sticky="w",padx=18,pady=7)
        ctk.CTkComboBox(self.opts,values=list(engine.VOICES),variable=self.voice).grid(row=2,column=1,sticky="w",pady=7)
        ctk.CTkLabel(self.opts,text="Zoom images").grid(row=3,column=0,sticky="w",padx=18,pady=7)
        ctk.CTkSlider(self.opts,from_=0,to=.15,number_of_steps=15,variable=self.zoom,width=300).grid(row=3,column=1,sticky="w",pady=7)
        ctk.CTkLabel(self.opts,textvariable=self.zoom).grid(row=3,column=2,padx=18)
        ctk.CTkLabel(self.opts,text="Nom du fichier").grid(row=4,column=0,sticky="w",padx=18,pady=(7,18))
        ctk.CTkEntry(self.opts,textvariable=self.output).grid(row=4,column=1,sticky="w",pady=(7,18))
        self.progress=ctk.CTkProgressBar(self.scroll); self.progress.set(0); self.progress.grid(row=3,column=0,sticky="ew",padx=24,pady=(2,6))
        self.log=ctk.CTkTextbox(self.scroll,height=120); self.log.grid(row=4,column=0,sticky="ew",padx=24,pady=(4,24))
    def set_format(self,v):
        self.format.set("9:16" if v.startswith("9:16") else "16:9")
    def add_scene(self,data=None):
        card=SceneCard(self.scene_area,self,len(self.scenes)+1,data); card.pack(fill="x",pady=7)
        self.scenes.append(card); self.renumber()
    def remove_scene(self,card):
        if len(self.scenes)<=1:return messagebox.showwarning("Ty-Videos-Studio","Il faut garder au moins une scène.")
        card.destroy(); self.scenes.remove(card); self.renumber()
    def renumber(self):
        for i,c in enumerate(self.scenes,1): c.title.configure(text=f"SCÈNE {i}")
    def pick_music(self):
        p=filedialog.askopenfilename(title="Choisir une musique",filetypes=[("Audio","*.mp3 *.wav *.m4a *.ogg"),("Tous","*.*")])
        if p:self.music.set(p)
    def write_log(self,s):
        self.after(0,lambda:(self.log.insert("end",s+"\n"),self.log.see("end")))
    def collect(self):
        scenes=[s.get() for s in self.scenes]
        for i,s in enumerate(scenes,1):
            if not s["text"]: raise ValueError(f"Scène {i}: texte vide.")
            if not s["background"] or not Path(s["background"]).exists(): raise ValueError(f"Scène {i}: fond invalide.")
            engine.check_media_format(s["background"],self.format.get())
        return scenes
    def render(self):
        try: scenes=self.collect()
        except Exception as e:return messagebox.showerror("Vérification",str(e))
        OUTPUT.mkdir(exist_ok=True); TEMP.mkdir(exist_ok=True)
        name=self.output.get().strip() or "ma_video.mp4"
        if not name.lower().endswith(".mp4"): name+=".mp4"
        out=OUTPUT/name
        voice,pitch=engine.VOICES[self.voice.get()]
        settings={"format":self.format.get(),"voice":voice,"pitch":pitch,"zoom":float(self.zoom.get()),
                  "music":self.music.get().strip(),"music_volume":.10,"fps":24,"project_dir":str(APP),"temp_dir":str(TEMP)}
        self.status.configure(text="● Rendu en cours",text_color="#ffbf4a"); self.progress.configure(mode="indeterminate"); self.progress.start()
        self.log.delete("1.0","end"); self.write_log("Démarrage du rendu…")
        def work():
            try:
                engine.render_project(scenes,settings,out,self.write_log)
                self.after(0,lambda:messagebox.showinfo("Terminé",f"Votre vidéo est prête :\n{out}"))
            except Exception as e:
                self.write_log("ERREUR : "+str(e)); self.write_log(traceback.format_exc())
                self.after(0,lambda:messagebox.showerror("Erreur de rendu",str(e)))
            finally:
                self.after(0,self.finish)
        threading.Thread(target=work,daemon=True).start()
    def finish(self):
        self.progress.stop(); self.progress.configure(mode="determinate"); self.progress.set(1)
        self.status.configure(text="● Prêt",text_color="#5bd28c")
    def save(self):
        data={"format":self.format.get(),"music":self.music.get(),"voice":self.voice.get(),"zoom":self.zoom.get(),"output":self.output.get(),
              "scenes":[s.get() for s in self.scenes]}
        CONFIG.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        self.write_log("Projet enregistré dans les données utilisateur.")
    def load(self):
        if not CONFIG.exists():return
        try:
            d=json.loads(CONFIG.read_text(encoding="utf-8"))
            self.set_format("9:16  Vertical" if d.get("format","9:16")=="9:16" else "16:9  Horizontal")
            self.music.set(d.get("music","")); self.voice.set(d.get("voice","Féminine — Denise"))
            self.zoom.set(float(d.get("zoom",0.06))); self.output.set(d.get("output","ma_video.mp4"))
            for s in d.get("scenes",[]): self.add_scene(s)
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
        except Exception as e:messagebox.showerror("Projet",str(e))
    def new(self):
        for s in self.scenes:s.destroy()
        self.scenes=[]; self.add_scene(); self.add_scene()
        self.music.set("");self.output.set("ma_video.mp4")
    def open_output(self):
        OUTPUT.mkdir(exist_ok=True); os.startfile(str(OUTPUT))
    def close(self):
        try:self.save()
        except:pass
        self.destroy()

if __name__=="__main__":
    App().mainloop()
