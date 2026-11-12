"""Native Setyawan--Curtarolo high-symmetry reciprocal-space paths.

THIRD-PARTY SOURCE NOTICE
-------------------------
The variant definitions, classification formulae, special-point formulae,
path strings, and primitive-cell matrices in this file are narrowly adapted
from ASE 3.29.0, ``ase/lattice/__init__.py`` (classes CUB through MCLC) and
``ase/dft/kpoints.py`` (``sc_special_points`` and ``parse_path_string``).
Copyright (C) 2010--2025 the ASE developers.  Those adapted portions are
provided under the BSD 2-Clause License; its notice is reproduced in
``THIRD_PARTY_NOTICES.md``.  MatSimPy modifications remove ASE objects and
imports, use plain NumPy data, map labels to pymatgen spelling, and cover the
14 three-dimensional Setyawan--Curtarolo Bravais families.  The special points
and paths of the five 2D Bravais lattices are adapted from the same ASE file
(classes OBL, RECT, CRECT, SQR and HEX2D); the classification of a layer from
its in-plane point group is MatSimPy's own.

Scientific source: W. Setyawan and S. Curtarolo, Computational Materials
Science 49, 299--312 (2010), Tables 2--19, doi:10.1016/j.commatsci.2010.05.010.
No pymatgen implementation or tables are included; pymatgen 2025.6.14 is used
only as an optional black-box parity oracle.
"""

import math
import re

import numpy as np

from .spacegroup import SpacegroupAnalyzer

G = "\\Gamma"
_D = np.pi / 180.0

_FIXED = {
    "cP": ({"G": (0, 0, 0), "M": (.5, .5, 0), "R": (.5, .5, .5), "X": (0, .5, 0)}, "GXMGRX,MR"),
    "cF": ({"G": (0, 0, 0), "K": (3/8, 3/8, 3/4), "L": (.5, .5, .5), "U": (5/8, .25, 5/8), "W": (.5, .25, .75), "X": (.5, 0, .5)}, "GXWKGLUWLK,UX"),
    "cI": ({"G": (0, 0, 0), "H": (.5, -.5, .5), "P": (.25, .25, .25), "N": (0, 0, .5)}, "GHNGPH,PN"),
    "tP": ({"G": (0, 0, 0), "A": (.5, .5, .5), "M": (.5, .5, 0), "R": (0, .5, .5), "X": (0, .5, 0), "Z": (0, 0, .5)}, "GXMGZRAZ,XR,MA"),
    "oP": ({"G": (0, 0, 0), "R": (.5, .5, .5), "S": (.5, .5, 0), "T": (0, .5, .5), "U": (.5, 0, .5), "X": (.5, 0, 0), "Y": (0, .5, 0), "Z": (0, 0, .5)}, "GXSYGZURTZ,YT,UX,SR"),
    "hP": ({"G": (0, 0, 0), "A": (0, 0, .5), "H": (1/3, 1/3, .5), "K": (1/3, 1/3, 0), "L": (.5, 0, .5), "M": (.5, 0, 0)}, "GMKGALHA,LM,KH"),
    "aP": ({"G": (0, 0, 0), "L": (.5, .5, 0), "M": (0, .5, .5), "N": (.5, 0, .5), "R": (.5, .5, .5), "X": (.5, 0, 0), "Y": (0, .5, 0), "Z": (0, 0, .5)}, "XGY,LGZ,NGM,RG"),
}

_NAMES_PATHS = {
    "BCT1": ("GMNPXZZ1", "GXMGZPNZ1M,XP"), "BCT2": ("GNPSS1XYY1Z", "GXYSGZS1NPY1Z,XP"),
    "ORCF1": ("GAA1LTXX1YZ", "GYTZGXA1Y,TX1,XAZ,LG"), "ORCF2": ("GCC1DD1LHH1XYZ", "GYCDXGZD1HC,C1Z,XH1,HY,LG"), "ORCF3": ("GAA1LTXX1YZ", "GYTZGXA1Y,XAZ,LG"),
    "ORCI": ("GLL1L2RSTWXX1YY1Z", "GXLTWRX1ZGYSW,L1Y,Y1Z"), "ORCC": ("GAA1RSTXX1YZ", "GXSRAZGYX1A1TY,ZT"),
    "RHL1": ("GBB1FLL1PP1P2QXZ", "GLB1,BZGX,QFP1Z,LP"), "RHL2": ("GFLPP1QQ1Z", "GPZQGFP1Q1LZ"),
    "MCL": ("GACDD1EHH1H2MM1M2XYY1Z", "GYHCEM1AXH1,MDZ,YD"),
    "MCLC1": ("GNN1FF1F2F3II1LMXX1X2YY1Z", "GYFLI,I1ZF1,YX1,XGN,MG"),
    "MCLC2": ("GNN1FF1F2F3II1LMXX1X2YY1Z", "GYFLI,I1ZF1,NGM"),
    "MCLC3": ("GFF1F2HH1H2IMNN1XYY1Y2Y3Z", "GYFHZIF1,H1Y1XGN,MG"),
    "MCLC4": ("GFF1F2HH1H2IMNN1XYY1Y2Y3Z", "GYFHZI,H1Y1XGN,MG"),
    "MCLC5": ("GFF1F2HH1H2II1LMNN1XYY1Y2Y3Z", "GYFLI,I1ZHF1,H1Y1XGN,MG"),
}


def _tokens(text):
    return re.findall(r"[A-Z](?:[123])?", text)


def _label(name, variant):
    if name == "G": return G
    if variant == "BCT2" and name.startswith("S"): name = "\\Sigma" + name[1:]
    return re.sub(r"([A-Za-z\\]+)([123])$", r"\1_\2", name)


def _paths(text, variant):
    return [[_label(x, variant) for x in _tokens(branch)] for branch in text.split(",")]


def _cell(key, a, b=None, c=None, alpha=None):
    if key == "cP": return a * np.eye(3)
    if key == "cF": return .5*np.array([[0,a,a],[a,0,a],[a,a,0]], float)
    if key == "cI": return .5*np.array([[-a,a,a],[a,-a,a],[a,a,-a]], float)
    if key == "tP": return np.diag([a,a,c])
    if key == "tI": return .5*np.array([[-a,a,c],[a,-a,c],[a,a,-c]], float)
    if key == "oP": return np.diag([a,b,c])
    if key == "oF": return .5*np.array([[0,b,c],[a,0,c],[a,b,0]], float)
    if key == "oI": return .5*np.array([[-a,b,c],[a,-b,c],[a,b,-c]], float)
    if key == "oC": return np.array([[.5*a,-.5*b,0],[.5*a,.5*b,0],[0,0,c]])
    if key == "hP": return np.array([[.5*a,-np.sqrt(3)*.5*a,0],[.5*a,np.sqrt(3)*.5*a,0],[0,0,c]])
    if key == "hR":
        x=np.cos(alpha*_D); x2=np.cos(alpha*_D/2); s2=np.sin(alpha*_D/2); q=x/x2
        return np.array([[a*x2,-a*s2,0],[a*x2,a*s2,0],[a*q,0,a*np.sqrt(1-q*q)]])
    if key == "mP": return np.array([[a,0,0],[0,b,0],[0,c*np.cos(alpha*_D),c*np.sin(alpha*_D)]])
    if key == "mC": return np.array([[.5*a,.5*b,0],[-.5*a,.5*b,0],[0,c*np.cos(alpha*_D),c*np.sin(alpha*_D)]])


def _definition(key, a=1., b=1., c=1., alpha=60., eps=2e-4):
    if key in _FIXED:
        pts, path = _FIXED[key]; variant={"cP":"CUB","cF":"FCC","cI":"BCC","tP":"TET","oP":"ORC","hP":"HEX","aP":"TRI1a"}[key]
    elif key == "tI":
        variant="BCT1" if c<a else "BCT2"; a2=a*a; c2=c*c
        if variant=="BCT1":
            e=.25*(1+c2/a2); vals=[[0,0,0],[-.5,.5,.5],[0,.5,0],[.25]*3,[0,0,.5],[e,e,-e],[-e,1-e,e]]
        else:
            e=.25*(1+a2/c2); z=.5*a2/c2; vals=[[0,0,0],[0,.5,0],[.25]*3,[-e,e,e],[e,1-e,-e],[0,0,.5],[-z,z,.5],[.5,.5,-z],[.5,.5,-.5]]
    elif key == "oF":
        d=1/a**2-1/b**2-1/c**2; variant="ORCF3" if abs(d)<eps else ("ORCF1" if d>0 else "ORCF2")
        xm=.25*(1+a*a/b**2-a*a/c**2); xp=.25*(1+a*a/b**2+a*a/c**2)
        if variant!="ORCF2": vals=[[0,0,0],[.5,.5+xm,xm],[.5,.5-xm,1-xm],[.5]*3,[1,.5,.5],[0,xp,xp],[1,1-xp,1-xp],[.5,0,.5],[.5,.5,0]]
        else:
            ph=.25*(1+c*c/b**2-c*c/a**2); de=.25*(1+b*b/a**2-b*b/c**2)
            vals=[[0,0,0],[.5,.5-xm,1-xm],[.5,.5+xm,xm],[.5-de,.5,1-de],[.5+de,.5,de],[.5]*3,[1-ph,.5-ph,.5],[ph,.5+ph,.5],[0,.5,.5],[.5,0,.5],[.5,.5,0]]
    elif key == "oI":
        variant="ORCI"; z=.25*(1+a*a/c**2); e=.25*(1+b*b/c**2); d=.25*(b*b-a*a)/c**2; m=.25*(a*a+b*b)/c**2
        vals=[[0,0,0],[-m,m,.5-d],[m,-m,.5+d],[.5-d,.5+d,-m],[0,.5,0],[.5,0,0],[0,0,.5],[.25]*3,[-z,z,z],[z,1-z,-z],[e,-e,e],[1-e,e,-e],[.5,.5,-.5]]
    elif key == "oC":
        variant="ORCC"; z=.25*(1+a*a/b**2); vals=[[0,0,0],[z,z,.5],[-z,1-z,.5],[0,.5,.5],[0,.5,0],[-.5,.5,.5],[z,z,0],[-z,1-z,0],[-.5,.5,0],[0,0,.5]]
    elif key == "hR":
        variant="RHL1" if alpha<90 else "RHL2"
        if variant=="RHL1":
            co=np.cos(alpha*_D); e=(1+4*co)/(2+4*co); n=.75-.5*e; vals=[[0,0,0],[e,.5,1-e],[.5,1-e,e-1],[.5,.5,0],[.5,0,0],[0,0,-.5],[e,n,n],[1-n,1-n,1-e],[n,n,e-1],[1-n,n,0],[n,0,-n],[.5]*3]
        else:
            e=1/(2*np.tan(alpha*_D/2)**2); n=.75-.5*e; vals=[[0,0,0],[.5,-.5,0],[.5,0,0],[1-n,-n,1-n],[n,n-1,n-1],[e,e,e],[1-e,-e,-e],[.5,-.5,.5]]
    elif key == "mP":
        variant="MCL"; co=np.cos(alpha*_D); e=(1-b*co/c)/(2*np.sin(alpha*_D)**2); n=.5-e*c*co/b
        vals=[[0,0,0],[.5,.5,0],[0,.5,.5],[.5,0,.5],[.5,0,-.5],[.5]*3,[0,e,1-n],[0,1-e,n],[0,e,-n],[.5,e,1-n],[.5,1-e,n],[.5,e,-n],[0,.5,0],[0,0,.5],[0,0,-.5],[.5,0,0]]
    elif key == "mC":
        co=np.cos(alpha*_D); si=np.sin(alpha*_D); num=b*co/c+b*b*si*si/(a*a)
        recip=np.linalg.inv(_cell(key,a,b,c,alpha)).T; u=recip/np.linalg.norm(recip,axis=1)[:,None]; kg=np.degrees(np.arccos(np.clip(u[0]@u[1],-1,1)))
        if abs(kg-90)<eps: variant="MCLC2"
        elif kg>90: variant="MCLC1"
        elif abs(num-1)<eps: variant="MCLC4"
        elif num<1: variant="MCLC3"
        else: variant="MCLC5"
        a2=a*a; b2=b*b; s2=si*si
        if variant in {"MCLC1","MCLC2"}:
            z=(2-b*co/c)/(4*s2); e=.5+2*z*c*co/b; ps=.75-a2/(4*b2*s2); ph=ps+(.75-ps)*b*co/c
            vals=[[0,0,0],[.5,0,0],[0,-.5,0],[1-z,1-z,1-e],[z,z,e],[-z,-z,1-e],[1-z,-z,1-e],[ph,1-ph,.5],[1-ph,ph-1,.5],[.5]*3,[.5,0,.5],[1-ps,ps-1,0],[ps,1-ps,0],[ps-1,-ps,0],[.5,.5,0],[-.5,-.5,0],[0,0,.5]]
        elif variant in {"MCLC3","MCLC4"}:
            m=.25*(1+b2/a2); de=b*c*co/(2*a2); z=m-.25+(1-b*co/c)/(4*s2); e=.5+2*z*c*co/b; ph=1+z-2*m; ps=e-2*de
            vals=[[0,0,0],[1-ph,1-ph,1-ps],[ph,ph-1,ps],[1-ph,-ph,1-ps],[z,z,e],[1-z,-z,1-e],[-z,-z,1-e],[.5,-.5,.5],[.5,0,.5],[.5,0,0],[0,-.5,0],[.5,-.5,0],[m,m,de],[1-m,-m,-de],[-m,-m,-de],[m,m-1,de],[0,0,.5]]
        else:
            z=.25*(b2/a2+(1-b*co/c)/s2); e=.5+2*z*c*co/b; m=.5*e+b2/(4*a2)-b*c*co/(2*a2); n=2*m-z; om=(4*n-1-b2*s2/a2)*c/(2*b*co); de=z*c*co/b+om/2-.25; rho=1-z*a2/b2
            vals=[[0,0,0],[n,n,om],[1-n,1-n,1-om],[n,n-1,om],[z,z,e],[1-z,-z,1-e],[-z,-z,1-e],[rho,1-rho,.5],[1-rho,rho-1,.5],[.5]*3,[.5,0,.5],[.5,0,0],[0,-.5,0],[.5,-.5,0],[m,m,de],[1-m,-m,-de],[-m,-m,-de],[m,m-1,de],[0,0,.5]]
    if key in _FIXED:
        points={_label(k,variant):tuple(map(float,v)) for k,v in pts.items()}
    else:
        names,path=_NAMES_PATHS[variant]; points={_label(n,variant):tuple(map(float,v)) for n,v in zip(_tokens(names),vals)}
        # pymatgen's pinned SC dictionary retains this boundary-only point for
        # MCLC2 but omits it from the otherwise shared MCLC1 point set.
        if variant == "MCLC1": points.pop("F_3", None)
    return variant, points, _paths(path,variant), _cell(key,a,b,c,alpha)


def _bravais(dataset):
    number=int(dataset.number if hasattr(dataset,"number") else dataset["number"]); symbol=dataset.international if hasattr(dataset,"international") else dataset["international"]; centering=str(symbol).strip()[0]
    if number>=195: system="c"
    elif number>=168: system="h"
    elif number>=143: return "hR" if centering=="R" else "hP"
    elif number>=75: system="t"
    elif number>=16: system="o"
    elif number>=3: system="m"
    else: return "aP"
    return system+(centering if centering in "PFIC" else "P")


def _parameters(key, conventional, primitive):
    abc=np.array([conventional.lattice.a,conventional.lattice.b,conventional.lattice.c],float)
    if key[0]=="c": return float(np.mean(abc)),1.,1.,60.
    if key[0]=="t": return float(np.mean(abc[:2])),1.,float(abc[2]),60.
    if key in {"oP","oF","oI"}: a,b,c=sorted(abc); return a,b,c,60.
    if key=="oC": a,b=sorted(abc[:2]); return a,b,float(abc[2]),60.
    if key=="hP": return float(np.mean(abc[:2])),1.,float(abc[2]),60.
    if key=="hR":
        p=primitive.lattice; return float(np.mean([p.a,p.b,p.c])),1.,1.,float(np.mean([p.alpha,p.beta,p.gamma]))
    if key in {"mP","mC"}:
        beta=float(conventional.lattice.beta); a,b,c=float(abc[1]),float(abc[0]),float(abc[2]); alpha=min(beta,180-beta)
        if b>c: b,c=c,b
        return a,b,c,alpha
    return 1.,1.,1.,60.


def _representative_paths():
    params={"cP":(3,1,1,60),"cF":(3,1,1,60),"cI":(3,1,1,60),"tP":(3,1,4,60),"tI":(3,1,4,60),"oP":(2,3,4,60),"oF":(2,3,4,60),"oI":(2,3,4,60),"oC":(2,3,4,60),"hP":(3,1,5,60),"hR":(3,1,1,70),"mP":(2,3,4,70),"mC":(2,3,4,70),"aP":(1,1,1,60)}
    return {k:(d[1],[e for branch in d[2] for e in zip(branch[:-1],branch[1:])]) for k,p in params.items() for d in [_definition(k,*p)]}


PATHS=_representative_paths()


# --- Two-dimensional (layer) crystals ---------------------------------------
#
# Special points and paths of the five 2D Bravais lattices follow ASE 3.29.0,
# ``ase/lattice/__init__.py`` classes OBL, RECT, CRECT, SQR and HEX2D (see the
# third-party notice above).  Each table is defined for ASE's canonical cell:
# OBL a < b, alpha < 90; RECT a < b; CRECT |a| = |b|, alpha < 90; SQR; HEX2D
# with gamma = 120 degrees.

_2D_VARIANTS = {"mp": "OBL", "op": "RECT", "oc": "CRECT", "tp": "SQR", "hp": "HEX2D"}
_2D_NAMES_PATHS = {
    "OBL": ("GYHCH1X", "GYHCH1XG"),
    "RECT": ("GXSY", "GXSYGS"),
    "CRECT": ("GXA1Y", "GXA1YG"),
    "SQR": ("GMX", "MGXM"),
    "HEX2D": ("GMK", "GMKG"),
}
# Points that never move with the metric; preferred when coincident points merge.
_2D_FIXED_LABELS = {"OBL": {"G", "Y", "C", "X"}, "CRECT": {"G", "Y"}}


def _2d_points(variant, a, b, alpha):
    """Fractional special points in the canonical 2D cell (a, b, alpha in degrees)."""
    if variant == "SQR":
        return [[0, 0], [.5, .5], [0, .5]]
    if variant == "RECT":
        return [[0, 0], [.5, 0], [.5, .5], [0, .5]]
    if variant == "HEX2D":
        return [[0, 0], [0, .5], [1/3, 1/3]]
    co = np.cos(alpha*_D)
    if variant == "CRECT":
        eta = np.sin(alpha*_D/2)**2/np.sin(alpha*_D)**2; xi = eta*co
        return [[0, 0], [eta, -eta], [.5+xi, .5-xi], [.5, .5]]
    eta = (1-a*co/b)/(2*np.sin(alpha*_D)**2); nu = .5-eta*b*co/a
    return [[0, 0], [0, .5], [eta, 1-nu], [.5, .5], [1-eta, nu], [.5, 0]]


def _primitive_integer(vector):
    vector = np.asarray(vector, dtype=int)
    divisor = math.gcd(abs(int(vector[0])), abs(int(vector[1])))
    return vector // divisor


def _null_vector(matrix):
    """Primitive integer vector spanning the kernel of a rank-1 2x2 integer matrix."""
    row = matrix[0] if np.any(matrix[0]) else matrix[1]
    return _primitive_integer([row[1], -row[0]])


def _gauss_reduce(basis, metric):
    """Lagrange--Gauss reduction of an integer 2D basis (columns) under a metric."""
    basis = np.array(basis, dtype=int)
    for _ in range(100):
        u, v = basis[:, 0], basis[:, 1]
        if u @ metric @ u > v @ metric @ v:
            basis = basis[:, ::-1].copy(); continue
        m = int(np.rint((u @ metric @ v)/(u @ metric @ u)))
        if m == 0:
            return basis
        basis[:, 1] = v - m*u
    raise ValueError("could not reduce the two-dimensional lattice")


class _Layer:
    """In-plane lattice and point group of a crystal with two periodic axes."""

    def __init__(self, structure, dataset):
        pbc = tuple(bool(x) for x in structure.pbc)
        self.axes = [i for i in range(3) if pbc[i]]
        (normal,) = [i for i in range(3) if not pbc[i]]
        vectors = np.asarray(structure.lattice.matrix, float)[self.axes]
        self.metric = vectors @ vectors.T
        self.blocks = []
        for rotation in np.asarray(dataset.rotations, dtype=int):
            # keep operations that map the layer plane onto itself
            if any(rotation[i, normal] or rotation[normal, i] for i in self.axes):
                continue
            block = rotation[np.ix_(self.axes, self.axes)]
            if not any(np.array_equal(block, seen) for seen in self.blocks):
                self.blocks.append(block)

    def length(self, n):
        return float(np.sqrt(n @ self.metric @ n))

    def angle(self, u, v):
        cosine = (u @ self.metric @ v)/(self.length(u)*self.length(v))
        return float(np.degrees(np.arccos(np.clip(cosine, -1, 1))))

    def classify(self):
        """Return (bravais, integer basis columns) adapted to the layer symmetry.

        Time reversal adds the in-plane 2-fold axis, so a k-path needs only the
        rotations and mirrors of the layer.  Without a mirror the IBZ is half the
        zone and the oblique path is used even for a square or hexagonal cell.
        """
        det = [round(np.linalg.det(b)) for b in self.blocks]
        mirrors = [b for b, d in zip(self.blocks, det) if d == -1]
        traces = {int(np.trace(b)) for b, d in zip(self.blocks, det) if d == 1}
        reduced = _gauss_reduce(np.eye(2, dtype=int), self.metric)
        if mirrors and traces & {1, -1}:
            u, v = reduced.T
            if self.angle(u, v) < 90: v = -v
            return "hp", np.column_stack([u, v])
        if mirrors and 0 in traces:
            return "tp", reduced
        if mirrors:
            mirror = mirrors[0]
            plus = _null_vector(mirror - np.eye(2, dtype=int))
            minus = _null_vector(mirror + np.eye(2, dtype=int))
            if abs(round(np.linalg.det(np.column_stack([plus, minus])))) == 1:
                if self.length(plus) > self.length(minus): plus, minus = minus, plus
                return "op", np.column_stack([plus, minus])
            u = (plus+minus)//2; v = mirror @ u
            if self.angle(u, v) > 90: v = -v
            return "oc", np.column_stack([u, v])
        u, v = reduced.T
        if self.angle(u, v) > 90: v = -v
        return "mp", np.column_stack([u, v])


def _merge_coincident(variant, points, path):
    """Drop labels whose point coincides with the previous one on the path.

    At the edges of their parameter ranges the OBL and CRECT tables put several
    labels on one point, e.g. H = C = H1 for a rectangular cell.  The fixed
    label of each run is kept."""
    fixed = _2D_FIXED_LABELS.get(variant, set())
    merged = []
    for label in path:
        if merged and np.allclose(points[label], points[merged[-1]], atol=1e-10):
            if label in fixed and merged[-1] not in fixed: merged[-1] = label
            continue
        merged.append(label)
    return merged


def _definition_2d(structure, dataset):
    layer = _Layer(structure, dataset)
    bravais, basis = layer.classify()
    variant = _2D_VARIANTS[bravais]
    u, v = basis.T
    names, path = _2D_NAMES_PATHS[variant]
    table = dict(zip(_tokens(names), _2d_points(variant, layer.length(u), layer.length(v), layer.angle(u, v))))
    # f_input = P^-T f_basis: k.a_j is invariant under the change of real-space basis
    to_input = np.linalg.inv(basis.astype(float)).T
    points = {}
    for name, fractional in table.items():
        full = np.zeros(3)
        full[layer.axes] = to_input @ np.asarray(fractional, float)
        points[name] = full
    # k -> -k (time reversal) maps the whole path onto an equivalent one; use
    # the orientation with fewer negative coordinates.
    coordinates = np.array(list(points.values()))
    if np.sum(-coordinates > 1e-12) > np.sum(coordinates > 1e-12):
        points = {name: -point + 0.0 for name, point in points.items()}
    path = _merge_coincident(variant, points, _tokens(path))
    points = {_label(n, variant): tuple(map(float, points[n])) for n in points if n in path}
    return bravais, variant, points, [[_label(n, variant) for n in path]]


class HighSymmKpath:
    """High-symmetry k-path of a crystal (Setyawan--Curtarolo; 2D per ASE).

    With three periodic axes the path is defined in the standard primitive
    cell, as in pymatgen.  With two periodic axes (a slab or monolayer,
    ``pbc`` with one False entry) the layer's 2D Bravais lattice is classified
    from its in-plane point group, and the k-points are fractional coordinates
    of the input cell's reciprocal lattice with zero along the non-periodic
    axis.  ``bravais`` is then one of ``mp, op, oc, tp, hp``.
    """

    def __init__(self,structure,symprec=.01,angle_tolerance=5.):
        self.structure=structure; self.analyzer=SpacegroupAnalyzer(structure,symprec,angle_tolerance)
        periodic=sum(bool(x) for x in getattr(structure,"pbc",(True,True,True)))
        if periodic==2:
            self.bravais,variant,points,paths=_definition_2d(structure,self.analyzer._dataset())
            self.kpath={"kpoints":points,"path":paths,"bravais":self.bravais,"variant":variant}
            self._reciprocal=2*np.pi*np.linalg.inv(np.asarray(structure.lattice.matrix,float)).T
            return
        if periodic!=3:
            raise ValueError(f"a k-path needs two or three periodic axes; pbc={tuple(structure.pbc)}")
        self.bravais=_bravais(self.analyzer._dataset())
        conventional=self.analyzer.get_conventional_standard_structure(); primitive=self.analyzer.get_primitive_standard_structure(); params=_parameters(self.bravais,conventional,primitive)
        # ASE's SC metric-boundary tolerance is 2e-4 and is deliberately
        # pinned independently of spglib's positional symmetry tolerance.
        variant,points,paths,cell=_definition(self.bravais,*params,eps=2e-4); self.kpath={"kpoints":points,"path":paths,"bravais":self.bravais,"variant":variant}
        self._reciprocal=2*np.pi*np.linalg.inv(primitive.lattice.matrix).T if self.bravais=="aP" else 2*np.pi*np.linalg.inv(cell).T

    def get_kpoints(self,line_density=20,coords_are_cartesian=False):
        if line_density<=0: raise ValueError("line_density must be positive")
        coordinates=[]; labels=[]
        for branch in self.kpath["path"]:
            for sl,el in zip(branch[:-1],branch[1:]):
                start=np.asarray(self.kpath["kpoints"][sl],float); end=np.asarray(self.kpath["kpoints"][el],float); intervals=int(math.ceil(np.linalg.norm((end-start)@self._reciprocal)*line_density))
                if not intervals: continue
                coordinates.extend(np.linspace(start,end,intervals+1).tolist()); labels.extend([sl]+[""]*(intervals-1)+[el])
        result=np.asarray(coordinates)
        return (result@self._reciprocal if coords_are_cartesian else result),labels
