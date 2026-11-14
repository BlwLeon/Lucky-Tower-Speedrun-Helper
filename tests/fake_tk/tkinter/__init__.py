"""Minimaler tkinter-Mock: zeichnet Canvas-Items mit PIL (nur für Layout-Vorschau/Tests)."""
import itertools
from . import font, messagebox, filedialog  # noqa
_ids = itertools.count(1)
class Tk:
    def __init__(self): self._after=[]; self.clip=""
    def title(self,*a): pass
    def resizable(self,*a): pass
    def bind(self,*a): pass
    def after(self,ms,fn): self._after.append(fn)
    def clipboard_clear(self): self.clip=""
    def clipboard_append(self,t): self.clip+=t
    def mainloop(self): pass
    def protocol(self,*a): pass
    def destroy(self): pass
    class tk:
        @staticmethod
        def call(*a): return "9.0-mock"
class Canvas:
    def __init__(self, root, width, height, **kw):
        self.w,self.h=width,height; self.items={}; self.binds={}
    def pack(self): pass
    def configure(self,**kw): pass
    def _new(self,typ,coords,kw):
        i=next(_ids); tags=kw.pop("tags",()); tags=(tags,) if isinstance(tags,str) else tuple(tags)
        self.items[i]=dict(type=typ,coords=list(coords),opts=kw,tags=tags); return i
    def create_rectangle(self,*c,**kw): return self._new("rect",c,kw)
    def create_oval(self,*c,**kw): return self._new("oval",c,kw)
    def create_polygon(self,*c,**kw):
        if len(c)==1: c=c[0]
        return self._new("poly",c,kw)
    def create_line(self,*c,**kw): return self._new("line",c,kw)
    def create_text(self,x,y,**kw): return self._new("text",(x,y),kw)
    def _sel(self,t): return [i for i,it in self.items.items() if i==t or t in it["tags"]]
    def delete(self,t):
        for i in self._sel(t): del self.items[i]
    def move(self,t,dx,dy):
        for i in self._sel(t):
            c=self.items[i]["coords"]; self.items[i]["coords"]=[v+(dx if k%2==0 else dy) for k,v in enumerate(c)]
    def bbox(self,t):
        xs=[];ys=[]
        for i in self._sel(t):
            c=self.items[i]["coords"]; xs+=c[0::2]; ys+=c[1::2]
        return (min(xs),min(ys),max(xs),max(ys)) if xs else None
    def itemconfigure(self,t,**kw):
        for i in self._sel(t): self.items[i]["opts"].update(kw)
    def coords(self,t,*c):
        for i in self._sel(t): self.items[i]["coords"]=list(c)
    def tag_bind(self,t,ev,fn): self.binds[(t,ev)]=fn
    def tag_unbind(self,t,ev): self.binds.pop((t,ev),None)
    def click(self,t): self.binds[(t,"<Button-1>")](None)
    def hover(self,t): self.binds[(t,"<Enter>")](None)
    def render(self,path):
        from PIL import Image, ImageDraw, ImageFont
        img=Image.new("RGB",(self.w,self.h),"white"); d=ImageDraw.Draw(img)
        def F(f):
            fam,size=f[0],f[1]; bold="bold" in f[2:] if len(f)>2 else False
            name="DejaVuSerif" if "Serif" in fam else "DejaVuSans"
            p=f"/usr/share/fonts/truetype/dejavu/{name}{'-Bold' if bold else ''}.ttf"
            return ImageFont.truetype(p,int(size*1.33))
        for it in self.items.values():
            o=it["opts"]; c=it["coords"]; fill=o.get("fill") or None; ol=o.get("outline","black") or None; w=int(o.get("width",1))
            if o.get("state")=="hidden": continue
            if it["type"]=="rect":
                x1,y1,x2,y2=c
                if x2<=x1: continue
                d.rectangle([x1,y1,x2,y2],fill=fill,outline=ol,width=w if ol else 0)
            elif it["type"]=="oval": d.ellipse(c,fill=fill,outline=ol,width=w if ol else 0)
            elif it["type"]=="poly":
                pts=list(zip(c[0::2],c[1::2]))
                if o.get("smooth") and len(pts)==12:
                    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
                    d.rounded_rectangle([min(xs),min(ys),max(xs),max(ys)],radius=12,fill=fill,outline=ol,width=w)
                else: d.polygon(pts,fill=fill,outline=ol,width=w)
            elif it["type"]=="line": d.line(c,fill=fill,width=w)
            elif it["type"]=="text":
                t=o.get("text","");
                if not t: continue
                a=o.get("anchor","center"); anc={"center":"mm","w":"lm","e":"rm"}[a]
                if "\n" in t: anc={"mm":"mm","lm":"lm","rm":"rm"}[anc]; d.multiline_text(tuple(c),t,font=F(o["font"]),fill=fill,anchor=anc,align="center")
                else: d.text(tuple(c),t,font=F(o["font"]),fill=fill,anchor=anc)
        img.save(path)
