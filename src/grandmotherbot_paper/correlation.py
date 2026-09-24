from __future__ import annotations

from math import sqrt

def _rank(values):
    order=sorted(enumerate(values), key=lambda x:x[1])
    ranks=[0.0]*len(values)
    i=0
    while i<len(order):
        j=i
        while j+1<len(order) and order[j+1][1]==order[i][1]:
            j+=1
        rank=(i+j+2)/2
        for k in range(i,j+1):
            ranks[order[k][0]]=rank
        i=j+1
    return ranks

def spearman(x,y):
    if len(x)!=len(y) or len(x)<2:
        raise ValueError("Spearman correlation requires equal-length arrays of at least two observations")
    rx,ry=_rank(list(x)),_rank(list(y))
    mx=sum(rx)/len(rx); my=sum(ry)/len(ry)
    num=sum((a-mx)*(b-my) for a,b in zip(rx,ry))
    den=sqrt(sum((a-mx)**2 for a in rx)*sum((b-my)**2 for b in ry))
    return num/den if den else 0.0
