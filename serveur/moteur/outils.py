"""Petits outils de calcul qui reproduisent le comportement d'Excel, là où Python fait autrement."""
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
import calendar


def arrondi(x, n=0):
    """ARRONDI d'Excel : au plus proche, le milieu s'éloigne de zéro (round() de Python arrondit au pair)."""
    if not x:
        return 0.0
    d = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP)
    return float(d)


def nombre(v, defaut=0.0):
    """Une saisie (texte, vide, '-', nombre) en nombre. '1 234,50' et '1234.5' sont acceptés."""
    if v is None or v == "" or v == "-":
        return defaut
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "").replace("\xa0", "").replace(" ", "").replace("€", "")
    if s in ("", "-"):
        return defaut
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return defaut


def egal(a, b):
    """Égalité de deux textes comme Excel : sans tenir compte de la casse."""
    return str(a or "").strip().casefold() == str(b or "").strip().casefold()


def nul(x, tol=0.005):
    """Montant nul au centime près (Excel compare au bit près : 1e-12 y passe pour « excès »)."""
    return abs(x or 0) < tol


def signalisation(x):
    """« ok » / « insuffisance » / « excès », comme les feuilles de cadrage."""
    if nul(x):
        return "ok"
    return "insuffisance" if x < 0 else "excès"


def div(a, b, defaut=0.0):
    """SIERREUR(a/b ; défaut)."""
    try:
        return a / b if b else defaut
    except (TypeError, ZeroDivisionError):
        return defaut


def fin_de_mois(d):
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def ajouter_mois(d, n):
    """MOIS.DECALER d'Excel : même jour n mois plus tard, ramené au dernier jour du mois si besoin."""
    m = d.month - 1 + n
    a, m = d.year + m // 12, m % 12 + 1
    return date(a, m, min(d.day, calendar.monthrange(a, m)[1]))


def datedif_mois(debut, fin):
    """DATEDIF(debut ; fin ; "M") : nombre de mois entiers révolus."""
    if fin < debut:
        return 0
    mois = (fin.year - debut.year) * 12 + fin.month - debut.month
    if fin.day < debut.day:
        mois -= 1
    return mois


def lire_date(v):
    """Une date saisie (date, 'AAAA-MM-JJ', 'JJ/MM/AAAA') ou None."""
    if not v:
        return None
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    try:
        if "/" in s:
            j, m, a = s.split("/")
            return date(int(a), int(m), int(j))
        a, m, j = s.split("-")
        return date(int(a), int(m), int(j))
    except ValueError:
        return None


def date_fr(d):
    return d.strftime("%d/%m/%Y") if d else ""


def veille(d):
    return d - timedelta(days=1)
