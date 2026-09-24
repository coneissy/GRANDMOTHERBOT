from pathlib import Path
import matplotlib.pyplot as plt

def _save(fig,path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,bbox_inches="tight")
    plt.close(fig)

def plot_gross_return_curve(curve,path,title="Gross Return curve"):
    fig,ax=plt.subplots(figsize=(8,4.5))
    xs=list(curve.keys()); ys=[float(v) for v in curve.values()]
    ax.plot([float(x) for x in xs],ys,marker="o",linewidth=1)
    ax.set_xlabel("Markout horizon (s)")
    ax.set_ylabel("Gross return")
    ax.set_title(title)
    ax.axvline(float(max(curve,key=curve.get)),linestyle="--",linewidth=1)
    _save(fig,path)

def plot_weekly_hhi(hhi_by_week,path,title="Weekly HHI"):
    fig,ax=plt.subplots(figsize=(8,4.5))
    xs=list(hhi_by_week.keys()); ys=[float(v) for v in hhi_by_week.values()]
    ax.plot(range(len(xs)),ys,linewidth=1)
    ax.set_xlabel("Week")
    ax.set_ylabel("HHI")
    ax.set_title(title)
    _save(fig,path)
