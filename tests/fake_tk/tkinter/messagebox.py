log=[]
def showerror(t,m): log.append(("error",t,m))
def showinfo(t,m): log.append(("info",t,m))
answer=True
def askyesno(t,m): log.append(("ask",t,m)); return answer

def askokcancel(t,m,**kw): log.append(("okcancel",t,m)); return answer
