import json, statistics as st, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family":"serif","font.size":8,"axes.spines.top":False,"axes.spines.right":False,
                     "axes.linewidth":0.6,"xtick.major.width":0.6,"ytick.major.width":0.6,"legend.frameon":False})
d=json.load(open("standing_anon.json")); o=[x or 0 for x in d["ours"]]; g=d["game_ids"]; rk=d["rank"]; gr=d["game_rank"]
cum=[];c=0
for x in o: c+=x; cum.append(c/1e3)
FAB=18.5; C1="#1f4e79"; GREEN="#2e7d32"; RED="#c62828"; GREY="#9e9e9e"
def phases(ax, label=True):
    ax.axvspan(0.5,FAB,color="#eeeeee",zorder=0); 
    if label:
        ax.text(9.5,0.97,"Python\nensemble",transform=ax.get_xaxis_transform(),ha="center",va="top",fontsize=6.5,color="#555")
        ax.text(22,0.97,"Fable in Claude Code (/loop) →",transform=ax.get_xaxis_transform(),ha="left",va="top",fontsize=6.5,color="#555")
    ax.set_xlim(0.5,len(g)+0.5)
def save(fig,n): fig.tight_layout(pad=0.3); fig.savefig("figures/"+n+".pdf"); fig.savefig("figures/"+n+".png",dpi=200); plt.close(fig)

# A: cumulative net vs field + rank inset axis
fig,ax=plt.subplots(figsize=(3.4,2.1)); phases(ax)
ax.plot(g,cum,color=C1,lw=1.6,label="our team")
ax.plot(g,[v/1e3 for v in d["field_best_other_cum"]],color=GREY,lw=0.9,ls="--",label="best other team")
ax.plot(g,[v/1e3 for v in d["field_median_cum"]],color=GREY,lw=0.9,ls=":",label="field median")
ax.set_xlabel("game"); ax.set_ylabel("cumulative net payoff (k€)"); ax.legend(loc="center left",fontsize=6.5)
ax.annotate(f"rank 1 of 12\n+{cum[-1]:.0f}k€",(g[-1],cum[-1]),xytext=(-62,-22),textcoords="offset points",fontsize=7,color=C1,fontweight="bold")
save(fig,"figA_cumulative_vs_field")

# B: per-game bars + rank
fig,(a1,a2)=plt.subplots(2,1,figsize=(3.4,2.6),sharex=True,gridspec_kw={"height_ratios":[2,1]}); phases(a1); phases(a2,False)
a1.bar(g,[x/1e3 for x in o],color=[GREEN if x>=0 else RED for x in o],width=0.8)
a1.axhline(0,color="k",lw=0.5); a1.set_ylabel("net payoff\nper game (k€)")
a2.step(g,rk,where="mid",color=C1,lw=1.2); R1=max(i for i in range(len(rk)) if rk[i]!=1)+2
a2.annotate(f"rank 1 since game {R1}",(R1,1),xytext=(60,6),fontsize=6.5,color=C1,arrowprops=dict(arrowstyle="-",lw=0.5,color=C1)); a2.set_ylim(12.5,0.5); a2.set_yticks([1,6,12]); a2.set_ylabel("overall\nrank (of 12)"); a2.set_xlabel("game")
save(fig,"figB_pergame_and_rank")

# C: before/after summary
pre,post=slice(0,18),slice(18,None)
stats=[("avg. net payoff\nper game (k€)",st.mean(o[pre])/1e3,st.mean(o[post])/1e3),
       ("games with\npositive net (%)",100*sum(x>0 for x in o[pre])/18,100*sum(x>0 for x in o[post])/len(o[post])),
       ("games ranked top 3\nof 12 teams (%)",100*sum(x<=3 for x in gr[pre])/18,100*sum(x<=3 for x in gr[post])/len(gr[post]))]
fig,axs=plt.subplots(1,3,figsize=(3.4,1.75))
for ax,(t,a,b) in zip(axs,stats):
    ax.bar([0,1],[a,b],color=[GREY,C1],width=0.6); ax.set_xticks([0,1],["ensemble\nG1–18",f"Fable\nG19–{g[-1]}"],fontsize=6.5); ax.set_title(t,fontsize=6.5)
    for i,v in enumerate([a,b]): ax.text(i,max(v,0)+0.03*max(a,b),f"{v:.1f}" if abs(v)<10 else f"{v:.0f}",ha="center",va="bottom",fontsize=6.5)
    ax.set_ylim(min(0,a,b)*1.6,max(a,b)*1.18)
    ax.axhline(0,color="k",lw=0.5); ax.tick_params(axis="y",labelsize=6)
save(fig,"figC_before_after")

# D: income vs costs, games 1-46 (own settlements)
ic=json.load(open("inc_cost.json")); gg=[x[0] for x in ic]
def roll(v,k=5): return [st.mean(v[max(0,i-k+1):i+1]) for i in range(len(v))]
fig,ax=plt.subplots(figsize=(3.4,1.9)); ax.axvspan(0.5,FAB,color="#eeeeee",zorder=0); ax.set_xlim(0.5,46.5)
ax.plot(gg,[x/1e3 for x in roll([x[1] for x in ic])],color=GREEN,lw=1.4,label="income as handyman (charges $a$)")
ax.plot(gg,[x/1e3 for x in roll([x[2] for x in ic])],color=RED,lw=1.4,label="costs as insurer (limits $b$)")
ax.set_xlabel("game"); ax.set_ylabel("k€, 5-game rolling mean"); ax.legend(fontsize=6.5,loc="upper left")
save(fig,"figD_income_vs_costs")

# ---- relative-to-field variants ----
fm=[x/1e3 for x in d["field_median_game"]]; q1=[x/1e3 for x in d["field_q25_game"]]; q3=[x/1e3 for x in d["field_q75_game"]]

# B2: per-game bars with field median, rank panel; all legend entries in one block above the figure
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
ORANGE="#e07b00"
fig,(a1,a2)=plt.subplots(2,1,figsize=(3.4,3.2),sharex=True,gridspec_kw={"height_ratios":[2,1.15]}); phases(a1); phases(a2,False)
a1.bar(g,[x/1e3 for x in o],color=[GREEN if x>=0 else RED for x in o],width=0.8,zorder=2)
a1.step(g,fm,where="mid",color="#212121",lw=0.8,zorder=3)
a1.axhline(0,color="k",lw=0.5); a1.set_ylabel("net payoff\nper game (k€)")
a2.step(g,rk,where="mid",color=C1,lw=1.0,zorder=2)
a2.scatter(g,gr,s=9,facecolors="none",edgecolors=ORANGE,linewidths=0.6,zorder=3)
a2.set_ylim(12.8,0.2); a2.set_yticks([1,3,6,9,12]); a2.set_ylabel("rank (of 12)"); a2.set_xlabel("game")
LK=dict(fontsize=6,handlelength=1.3,columnspacing=0.9,frameon=False,loc="lower center",borderaxespad=0.15)
a1.legend(handles=[Patch(color=GREEN,label="our net: profit"),Patch(color=RED,label="our net: loss"),
                   Line2D([],[],color="#212121",lw=0.8,label="other 11 teams (median)")],ncol=3,bbox_to_anchor=(0.5,1.0),**LK)
a2.legend(handles=[Line2D([],[],color=C1,lw=1.0,label="our overall rank (cumulative)"),
                   Line2D([],[],ls="none",marker="o",markersize=3.2,markerfacecolor="none",markeredgecolor=ORANGE,markeredgewidth=0.6,label="our rank in that game")],
          ncol=2,bbox_to_anchor=(0.5,1.0),**LK)
fig.tight_layout(pad=0.3,h_pad=1.4); fig.savefig("figures/figB2_pergame_vs_field.pdf"); fig.savefig("figures/figB2_pergame_vs_field.png",dpi=200); plt.close(fig)

# E: cumulative lead over the field
fig,ax=plt.subplots(figsize=(3.4,1.9)); phases(ax)
ax.plot(g,[c-b/1e3 for c,b in zip(cum,d["field_best_other_cum"])],color=C1,lw=1.5,label="lead over best other team")
ax.plot(g,[c-b/1e3 for c,b in zip(cum,d["field_median_cum"])],color=C1,lw=1.0,ls="--",label="lead over field median")
ax.axhline(0,color="k",lw=0.5); ax.set_xlabel("game"); ax.set_ylabel("cumulative lead (k€)")
ax.legend(fontsize=6.5,loc="center left",bbox_to_anchor=(0.0,0.55))
save(fig,"figE_lead_over_field")

# ---- Fig 1: combined, full text width (6.85 in), drawn at 1:1 scale ----
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
ORANGE="#e07b00"
fig=plt.figure(figsize=(7.0,2.35))
outer=GridSpec(1,2,width_ratios=[2.15,1],wspace=0.32,figure=fig)
right=GridSpecFromSubplotSpec(3,1,subplot_spec=outer[1],hspace=1.35)
a1=fig.add_subplot(outer[0])
F1=22  # first Fable /loop game; keep in sync with fetch.py
for ax in (a1,): ax.axvspan(0.5,F1-0.5,color="#eeeeee",zorder=0); ax.set_xlim(0.5,len(g)+0.5)
a1.text((F1-0.5)/2+0.25,0.95,"models +\nPython pricing",transform=a1.get_xaxis_transform(),ha="center",va="top",fontsize=7,color="#555")
a1.text(F1+1.5,0.95,"Fable agent in Claude Code →",transform=a1.get_xaxis_transform(),ha="left",va="top",fontsize=7,color="#555")
a1.bar(g,[x/1e3 for x in o],color=[GREEN if x>=0 else RED for x in o],width=0.8,zorder=2)
import matplotlib.patheffects as pe
HALO=[pe.Stroke(linewidth=2.6,foreground="white"),pe.Normal()]
a1.step(g,fm,where="mid",color="black",lw=1.3,zorder=4,path_effects=HALO)
a1.axhline(0,color="k",lw=0.5); a1.set_ylabel("net per game (k€)"); a1.set_xlabel("game")
CAP=105  # clip the axis so one outlier game does not flatten all others; clipped bars are labelled
lo=min(min(fm),min(x/1e3 for x in o))*1.1; a1.set_ylim(lo,CAP)
for gi,x in zip(g,o):
    if x/1e3>CAP: a1.text(gi,CAP*0.97,f"game {gi}: {x/1e3:.0f}k ↑",ha="right",va="top",fontsize=7,color=GREEN,fontweight="bold")
LK=dict(fontsize=7,handlelength=1.3,columnspacing=1.0,frameon=False,loc="lower left",borderaxespad=0.15)
a1.legend(handles=[Patch(color=GREEN,label="our net: profit"),Patch(color=RED,label="our net: loss"),
                   Line2D([],[],color="black",lw=1.3,label="other 11 teams (median)")],ncol=3,bbox_to_anchor=(0,1.0),**LK)
pre,post=slice(0,F1-1),slice(F1-1,None)
rstats=[("avg. net per game (k€)",st.mean(o[pre])/1e3,st.mean(o[post])/1e3,"{:.1f}"),
        ("games with positive net (%)",100*sum(x>0 for x in o[pre])/len(o[pre]),100*sum(x>0 for x in o[post])/len(o[post]),"{:.0f}"),
        ("games ranked top 3 of 12 (%)",100*sum(x<=3 for x in gr[pre])/len(gr[pre]),100*sum(x<=3 for x in gr[post])/len(gr[post]),"{:.0f}")]
for i,(t,a,b,fmt) in enumerate(rstats):
    ax=fig.add_subplot(right[i]); ax.barh([1,0],[a,b],color=[GREY,C1],height=0.65)
    ax.set_yticks([1,0],[f"games 1–{F1-1}",f"games {F1}–{g[-1]}"],fontsize=7); ax.set_title(t,fontsize=7.5,loc="left",pad=3)
    hi=max(a,b); ax.set_xlim(min(0,a,b)*1.0-(0.12*hi if min(a,b)<0 else 0),hi*1.22); ax.axvline(0,color="k",lw=0.5)
    for y,v in ((1,a),(0,b)): ax.text(max(v,0)+0.02*hi,y,fmt.format(v),va="center",ha="left",fontsize=7)
    ax.tick_params(axis="x",labelsize=6.5); ax.spines["left"].set_visible(False); ax.tick_params(axis="y",length=0)
fig.subplots_adjust(left=0.075,right=0.985,top=0.9,bottom=0.17)
fig.savefig("figures/fig1_combined.pdf"); fig.savefig("figures/fig1_combined.png",dpi=200); plt.close(fig)
