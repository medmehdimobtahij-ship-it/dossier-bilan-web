# Dossier Bilan : écarts avec l'Excel d'origine

Référence : le classeur Excel métier d'origine du cabinet (42 feuilles, environ 20 000 formules, macros VBA). Il n'est **pas publié** : c'est un document interne, et il contenait encore des données de clients.

Le moteur de Dossier Bilan reprend les formules de l'Excel une à une. La règle est simple : **même résultat que l'Excel, sauf là où l'Excel se trompe**. Chaque écart volontaire est listé ci-dessous, vérifié sur la vraie formule de l'Excel, et couvert par un test automatique (`tests/test_moteur.py`).

## Comment la fidélité est prouvée

Le banc `tests/parite/excel_parite.py` génère des dossiers fictifs complets : une balance d'environ 100 à 350 comptes, plus des saisies dans toutes les feuilles (affectations, associés, cadrage du CA, TVA, fiscal, TNS, paie…). Il écrit chaque dossier dans une **copie** de l'Excel, laisse Excel recalculer, relit environ 2 500 cellules par dossier et les compare au moteur, au centime près. L'original n'est jamais modifié.

Résultat de la dernière campagne (le banc écrit le détail dans `tests/parite/rapport_parite.json`, non versionné) :

| Scénarios | Cellules comparées | Identiques | Écarts imprévus | Écarts expliqués |
|---|---|---|---|---|
| 10 dossiers standards (graines 1 à 10) | 24 910 | 24 829 | **0** | 81 (corrections n°8 : 47, n°2 : 30, n°4 : 4) |
| Quote-part en commun 655/755 (101) | 2 475 | 2 435 | **0** | 40 (correction n°1) |
| Gros déficit antérieur (102) | 2 510 | 2 490 | **0** | 20 (correction n°6) |
| Grosse balance de 351 comptes (103) | 5 631 | 5 575 | **0** | 56 (limite n°10) |

Au total, **35 526 cellules comparées, aucun écart imprévu.** Temps de calcul sur ces dossiers : l'Excel met 2 à 5 secondes par recalcul (sans compter l'ouverture, les liens morts et les macros) ; le moteur met **moins de 10 millisecondes**.

## Corrections (le moteur fait différemment, exprès)

| N° | Feuille et cellules | Défaut de l'Excel | Ce que fait Dossier Bilan |
|---|---|---|---|
| 1 | SIG E881, E930, E1077 | 655 et 755 portent le même libellé de rubrique ; le SIG somme cette rubrique en « + » puis en « − », donc **la quote-part est comptée deux fois** dans le résultat courant. Le contrôle « résultat SIG = résultat comptable » tombe alors en erreur. | Deux rubriques distinctes : quote-part bénéficiaire (755) en produit, quote-part déficitaire (655) en charge. |
| 2 | TVA_Cadrage_Flux H17:J17 | Pour les colonnes 0 %, INTRA et EXTRA, la formule divise par le taux de la colonne **voisine** (0 ou un texte) : erreur, puis 0, donc la ligne affiche toujours « ok », même avec un vrai écart. | Sans TVA, la régularisation s'ajoute telle quelle à l'écart de base. |
| 3 | Récap_IR F27 (case 5ND) | La case micro-LMNP reprend l'indemnité des **revenus fonciers** (QPLOYER) au lieu de l'indemnité micro-LMNP. | 5ND = indemnité micro-LMNP. |
| 4 | AGO_N_1 lignes 26 à 29 | Cotisations TNS théoriques sur dividendes : 25 % pour l'associé 1, **40 % pour les associés 2 à 6** (formule recopiée de travers). AGO_N applique 25 % partout. | Un seul taux, réglable par dossier (onglet Dossier), 25 % par défaut. **À faire valider (Q3).** |
| 5 | Caché_Provision_TNS C12 | PASS figé à 47 100 € (valeur 2025). | PASS selon l'année de clôture (2026 : 48 060 €), modifiable. |
| 6 | Résultat_Fiscal D37 et D39 | L'imputation du déficit antérieur n'est **pas plafonnée au bénéfice** : avec 10 000 € de bénéfice et 50 000 € de déficit, l'Excel impute 50 000 €. Le résultat fiscal devient −40 000 € et le déficit restant 0 : **40 000 € de déficit reportable disparaissent**. Le faux déficit se propage au récapitulatif IR (cases 5KF et 5NF ; vu dans un essai : −428 622 €). | Imputation = min(déficit ; bénéfice ≤ 1 M€, ou 1 M€ + 50 % au-delà) (art. 209 I du CGI). Le déficit non imputé reste reportable. |
| 7 | Caché_Intermédiaire | Si un compte apparaît deux fois dans la balance collée, les colonnes se décalent (FILTRE garde les doublons, RECHERCHEV ne lit que le premier) : montants faux et #N/A. | Les doublons sont additionnés. |
| 8 | AGO_N H17:H18 | Situation après l'AG : les subventions d'investissement (13) et les provisions réglementées (14) **disparaissent** des capitaux propres. | Elles restent dans les capitaux propres après l'AG. |
| 9 | Liasse_fiscale E7:E10 | La ventilation du CA (marchandises / services, France / international) ne lit que les **13 premiers** comptes 70 (Cadrage_CA D7:D19), alors que la liste en contient jusqu'à 26. | Tous les comptes 70 sont lus. |

### Limite n°10 : les plafonds de taille de l'Excel

Au-delà de ces seuils, l'Excel affiche #EPARS! ou ignore des lignes sans prévenir. Dossier Bilan n'a aucune limite.

| Feuille | Plafond de l'Excel |
|---|---|
| Bal_Comparative | 992 comptes |
| Feuilles de cycle (Comptes_…) | 144 comptes par cycle (zone B6:I150) |
| Cadrage_CA | 26 comptes 70 : au-delà, **tout le cadrage du CA et de la TVA tombe à zéro** (scénario 103) |
| TVA_Cadrage_Solde | 15 comptes 4457 |
| Caché_Emprunts | 9 emprunts |
| TVA_Récap_Interne | 22 mois |

## Autres constats sur le fichier

- **Données d'anciens clients restées dans le modèle** : journal de paie complet, récapitulatif de TVA d'un dossier, liste de comptes avec commentaires (Caché_Commentaires), nom d'un gérant dans deux feuilles. Chaque nouveau dossier créé à partir de ce modèle les embarque (problème de confidentialité, résolu par construction dans l'application : un dossier ne contient que ses propres données).
- **23 noms définis pointent vers un classeur externe disparu** (`[1]0-SIG`, `[1]CHIFFRE CLES`…) : ce sont eux qui déclenchent le message « mettre à jour les liaisons ». Ils ne servent à aucun calcul.
- La feuille Caché_SIGOLD n'est plus utilisée.
- Les signalisations « ok / insuffisance / excès » comparent à zéro au bit près : un écart de 0,0000001 € donne « excès ». Dossier Bilan compare au centime.
- Les macros (Module2) ne calculent rien : elles vident la balance et préservent les statuts et commentaires d'un exercice à l'autre. Dossier Bilan le fait par la base de données (reprise de l'exercice précédent à la création du dossier).

## Points à faire valider par l'expert-comptable

Ce sont des choix de doctrine, pas des bugs : ils relèvent de l'expert-comptable signataire. Pour chacun, Dossier Bilan fait **comme l'Excel** en attendant la décision.

| N° | Question | Comportement actuel |
|---|---|---|
| Q1 | Les comptes **79 (transferts de charges)** et quelques racines absentes du tableau des rubriques (689, 789, 650…) ne sont rangés dans aucune rubrique du SIG. Où les mettre ? | Hors SIG, comme l'Excel ; l'application les liste en rouge en tête du SIG et dans les contrôles. |
| Q2 | Cadrage du CA, ligne « Débours et autres produits (hors 70) » : seules les **cessions** entrent dans la facturation TTC, pas les débours. Est-ce voulu ? | Cessions seules. |
| Q3 | Taux des cotisations TNS sur la part des dividendes au-delà de 10 % : 25 % ? 40 % ? | 25 %, réglable par dossier. |
| Q4 | Plafond du taux réduit de 15 % la première année : l'Excel compte les mois entiers plus les jours du premier mois divisés par 30 (juillet-décembre = 6,03 mois). Faut-il un prorata en jours ? | Formule de l'Excel. |
| Q5 | AG à tenir sur N, régime « EI IS » : le plafond de 10 % est calculé sur le résultat **N-1**. Ne devrait-il pas porter sur N ? | Résultat N-1. |
| Q6 | TVA déductible (lignes 19 à 2C) : l'Excel la lit dans la colonne « Base HT » du récapitulatif Pennylane. À vérifier sur un vrai export. | Colonne « Base HT ». |
