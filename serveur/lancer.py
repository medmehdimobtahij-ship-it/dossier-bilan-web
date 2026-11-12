"""Lance Dossier Bilan sur ce poste : http://localhost:8095, et http://<adresse du poste>:8095 depuis le réseau local.

Serveur waitress (fait pour la production, sous Windows comme sous Linux).
Variables : BILAN_PORT (8095 par défaut), BILAN_HOTE (0.0.0.0), BILAN_DEMO=1 (démo hors ligne, dossiers fictifs).
"""
import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from waitress import serve  # noqa: E402

import comptes  # noqa: E402
from app import creer_app  # noqa: E402


def adresse_locale():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # aucun paquet n'est envoyé : sert seulement à connaître l'adresse du poste
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def deja_lance(port):
    """Un serveur répond déjà sur ce port ? (Sous Windows, deux serveurs peuvent écouter le même port : c'est alors
    l'ancien, avec l'ancienne version, qui répond.)"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


if __name__ == "__main__":
    port = int(os.environ.get("BILAN_PORT", "8095"))
    if deja_lance(port):
        print(f"\n  Dossier Bilan tourne déjà sur ce poste (port {port}).")
        print("  Pour lancer la nouvelle version : arrêtez l'ancien serveur (ou changez BILAN_PORT), puis relancez.\n")
        sys.exit(1)
    crees = comptes.initialiser()
    print("\n  Dossier Bilan\n  -------------")
    print(f"  Sur ce poste      : http://localhost:{port}")
    if os.environ.get("BILAN_DEMO") != "1":  # la démo n'écoute que ce poste (127.0.0.1)
        print(f"  Depuis le réseau  : http://{socket.gethostname()}:{port}   (ou http://{adresse_locale()}:{port})")
    print()
    if os.environ.get("BILAN_DEMO") == "1":
        print("  MODE DÉMO : dossiers fictifs, connexion automatique (compte demo / demo), aucun service externe.\n")
    elif os.environ.get("BILAN_SANS_MDP") == "1":
        print("  Sans mot de passe : chacun choisit son nom à l'ouverture (réservé à un réseau local de confiance).\n")
    elif crees:
        print("  Comptes créés. Mots de passe PROVISOIRES (affichés une seule fois, à changer dans Paramètres › Mon compte) :")
        for identifiant, mdp in crees.items():
            print(f"     {identifiant:<8} {mdp}")
        print()
    print("  Laissez cette fenêtre ouverte : la fermer (ou Ctrl+C) arrête le serveur.\n")
    serve(creer_app(), host=os.environ.get("BILAN_HOTE", "127.0.0.1" if os.environ.get("BILAN_DEMO") == "1" else "0.0.0.0"), port=port, threads=8, ident="Dossier Bilan")
