"""Réinitialise le mot de passe d'un compte (mot de passe oublié) : python gerer_comptes.py admin"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import comptes  # noqa: E402

if __name__ == "__main__":
    comptes.initialiser()
    if len(sys.argv) != 2 or sys.argv[1].lower() not in comptes.lire():
        print("Usage : python gerer_comptes.py <identifiant>   (comptes : " + ", ".join(comptes.lire()) + ")")
        sys.exit(1)
    mdp = comptes.provisoire()
    c = comptes.lire(); c[sys.argv[1].lower()]["hash"] = comptes.generate_password_hash(mdp); comptes.ecrire(c)
    print(f"Nouveau mot de passe provisoire pour {sys.argv[1].lower()} : {mdp}")
