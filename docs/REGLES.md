# Dossier Bilan : règles de calcul

Ce document décrit, feuille par feuille, ce que calcule le dossier bilan. C'est la traduction en clair des formules du classeur Excel métier d'origine (un gros classeur à macros de cabinet, non publié), telles que le moteur les applique (`serveur/moteur/`). Les écarts volontaires avec l'Excel sont signalés par « correction n° » et détaillés dans [ECARTS_EXCEL.md](ECARTS_EXCEL.md).

Convention des soldes, la même que l'Excel : **solde = débit − crédit**. Un produit, une dette ou un capital est donc négatif.

## 1. Balance comparative (BalanceP, Bal_Comparative)

- Entrée : la balance N et N-1 par compte, importée de Pennylane ou d'un fichier.
- Pour chaque compte : variation = N − N-1 ; variation % = variation / N-1 (0 si N-1 est nul).
- **Résultat N** = −(somme des soldes N des classes 6 et 7) ; même calcul en N-1. Libellé « Bénéfice », « Déficit » ou « Résultat ».
- Contrôles : balance N et N-1 équilibrées (total nul au centime) ; résultat du SIG = résultat de la balance.
- Rubrique du SIG d'un compte de classe 6 ou 7 : on cherche sa racine à 2 chiffres dans le tableau des rubriques, puis à 3, puis à 4 (tableau complet dans `referentiel.py`, repris de Caché_Mapping).

## 2. Feuilles de révision par cycle

| Cycle | Comptes |
|---|---|
| Comptes d'attente et de régularisation | 47, 58 |
| Trésorerie | 5 sauf 58 |
| Comptes courants | 45, 46 |
| Emprunts | 16, 661 |
| Social | 42, 43, 64 |
| État | 44, 63, 69 |
| Charges externes | 60, 61, 62 |
| Immobilisations | 2, 681 |
| Capitaux propres | 1 sauf 15 et 16 |

Chaque compte porte un statut et un commentaire de révision. Ils sont gardés par numéro de compte et repris d'un exercice à l'autre, comme le faisaient les macros Clearbalance et Input1.

## 3. Soldes intermédiaires de gestion (SIG)

Chaque rubrique additionne les comptes qui lui sont rattachés : les produits en positif (−solde), les charges en positif (+solde).

- Chiffre d'affaires = −(comptes 70).
- Marge commerciale = ventes de marchandises (707, 7097) − coût d'achat des marchandises vendues (607, 6037, 6097).
- Production de l'exercice = production vendue + stockée + immobilisée.
- Marge globale = marge commerciale + production − autres consommations de la marge globale (600 à 609 hors 607).
- Valeur ajoutée = marge globale − autres consommations en provenance des tiers (61, 62).
- EBE = valeur ajoutée + subventions (74) − impôts et taxes (63) − charges de personnel (64).
- Résultat d'exploitation = EBE + reprises (781) − dotations (681) + quote-part de subventions virée (747) + produits de cession (757) − VNC cédées (657) + autres produits − autres charges.
- Résultat courant avant impôts = résultat d'exploitation + quote-part bénéficiaire en commun (755) − quote-part déficitaire (655) + produits financiers (76, 786) − charges financières (66, 686). *Correction n°1.*
- Résultat exceptionnel = produits exceptionnels (77, 787) − charges exceptionnelles (67, 687).
- Résultat de l'exercice = RCAI + résultat exceptionnel − participation (691) − impôts sur les bénéfices (690, 692 à 699).
- Pour chaque ligne : % du CA, N-1, variation, variation %, et le détail des comptes.

## 4. Capitaux propres (Capitaux)

- Comptes suivis : 101, 104, 105, 1061, 1063, 1064, 1068, 110, 119, 120, 129, 13, 14 (somme des comptes commençant par la racine). Alerte si 120 ou 129 n'est pas soldé.
- **Affectation du résultat N-1** : résultat N-1 + variations des réserves (1061, 1063, 1064, 1068) + variation du report à nouveau et des comptes de résultat (110, 119, 120, 129) − dividendes, compte de l'exploitant et autres affectations saisis = reste à justifier (doit être nul).
- Continuité : capitaux propres hors résultat = −Σ comptes suivis ; capitaux propres totaux = hors résultat + résultat ; rapport au capital social. L'application signale en plus des capitaux propres inférieurs à la moitié du capital.

## 5. Assemblées générales (AGO_N_1, AGO_N, Caché_Données)

**Affectation du résultat N.**
- Distribuable = résultat N − soldes N de 1068, 110, 119, 120, 129 (réserves libres et report à nouveau).
- Réserve légale : si elle n'atteint pas 10 % du capital et qu'il y a un bénéfice distribuable, la dotation = min(reste pour atteindre 10 % du capital ; 5 % du résultat plafonné à 10 % du capital), et 0 si le distribuable est inférieur à ces 5 %.
- Puis les affectations saisies (réserve statutaire, réglementée, autres réserves, dividendes, compte courant). Le reste va en report à nouveau créditeur (positif) ou débiteur (négatif).
- Situation après l'AG : les réserves reçoivent leurs dotations, le résultat est soldé, le report à nouveau est remplacé. *Correction n°8 : les comptes 13 et 14 restent.*

**Répartition des dividendes, par associé (6 au plus).**
- % de détention = parts / total des parts ; dividende affecté = % × dividendes ; dividende retenu (case 2DC) = montant forcé s'il est saisi, sinon dividende affecté.
- Quote-part pour un TNS : à l'AG N, % × (capital + primes) + compte courant moyen ; à l'AG N-1, saisie.
- Soumis aux prélèvements sociaux (2BH) : personne morale → 0 ; TNS → min(retenu ; 10 % de la quote-part) ; non TNS → retenu ; EI à l'IS → min(retenu ; 10 % du résultat N-1).
- Soumis aux cotisations sociales (2CG) = retenu − 2BH (0 pour une personne morale).
- Prélèvements sociaux = 2BH × taux (17,2 % en N-1, 18,6 % en N, modifiables).
- Précompte IR 12,8 % (2CK) = 12,8 % × retenu, sauf dispense ou personne morale.
- Net versé = retenu − prélèvements sociaux − précompte.
- Coût pour l'entreprise = retenues + cotisations TNS théoriques (2CG × taux, *correction n°4*) − économie d'IS (25 % des cotisations).

## 6. Cadrage du chiffre d'affaires (Cadrage_CA)

- Chaque compte 70 reçoit un taux (20, 10, 8,5, 5,5, 0, INTRA, EXTRA) et un type (Marchandises ou Services, pour la liasse).
- Par taux : CA HT réalisé ; corrections de début d'exercice (extournes FAE − AAE − PCA de N-1) et de fin d'exercice (− FAE + AAE + PCA de N) ; CA facturé = réalisé + corrections ; TVA = CA facturé × taux ; autres produits (cessions) et leur TVA ; **facturation TTC** = somme.
- Soldes clients TTC N-1 et N par taux (411, 416, 4191), rapprochés de la balance.
- Corrections exceptionnelles TTC = −(pertes − produits exceptionnels) × (1 + taux).

## 7. TVA

**Déclarations (TVA_Récap_Interne).** Pour chaque mois de l'exercice, les lignes de la CA3 reprises du récapitulatif Pennylane. TVA brute = Σ arrondi(base × taux) pour 08 (20 %), 09 (5,5 %), 9B (10 %), 10 (8,5 %), + lignes 15 et 5B. TVA déductible = lignes 19 à 2C. Crédit (25) = déductible − brute si positif, sinon TVA nette due (28) = brute − déductible. Totaux sur l'exercice.

**Cadrage sur le solde (TVA_Cadrage_Solde).** TVA théorique = −(solde client TTC / (1 + taux) × taux), comparée au solde des comptes 4457 de ce taux, en N-1 et en N. Écart en TVA et en base HT.

**Cadrage sur les flux (TVA_Cadrage_Flux).** Encaissements TTC = solde client N-1 + facturation TTC + corrections − solde client N. Base HT théorique = encaissements / (1 + taux). Base déclarée : 20 % = ligne 08 − B2 − A4 − A3 − A2 ; 10 % = 9B ; 8,5 % = 10 ; 5,5 % = 09 ; saisie pour 0 %, INTRA et EXTRA. Écart, puis écart après la régularisation 4458 (*correction n°2* pour les colonnes sans TVA), puis différence à justifier après les écarts de solde.

## 8. Résultat fiscal et IS (Résultat_Fiscal)

- Réintégrations : IS (695), amendes (6582) et dons (6238) repris de la balance (modifiables), plus les saisies (TVS, loyers de crédit-bail non déductibles, taxe sur les bureaux, abandon de créance, résultat de SCI à l'IR, amortissements LMNP, divers).
- Déductions : dividendes mère-fille × (1 − quote-part de frais, 5 %), plus les saisies.
- Résultat avant imputation = bénéfice + déficit − déductions + réintégrations.
- Déficit imputé = min(déficit antérieur ; plafond), plafond = bénéfice jusqu'à 1 M€, puis 1 M€ + 50 % au-delà. *Correction n°6.*
- IS : taux réduit 15 % jusqu'à 42 500 € (au prorata la première année, *voir Q4*), 25 % au-delà, arrondi à l'euro. Non soumise à l'IS → 0.
- Résultat net comptable ajusté = bénéfice + IS comptabilisé − IS calculé + déficit.

## 9. Emprunts et liasse (Caché_Emprunts, Liasse_fiscale)

- Emprunts (164) : capital restant dû N-1 et N d'après la balance ; CRDU N+1 et N+5 et montant souscrit saisis. Remboursé = CRDU N-1 − CRDU N + souscrit ; à un an au plus = CRDU N − CRDU N+1 ; un à cinq ans = CRDU N+1 − CRDU N+5 ; plus de cinq ans = CRDU N+5.
- Liasse : CA ventilé (*correction n°9*), exceptionnel, emprunts, résultat fiscal, déficit reportable, dividendes, prélèvements sur réserves (hausse du 1068 au débit), TVA collectée théorique, CVAE (1329 dès 500 000 € de CA, feuillet entre 152 500 € et 500 000 €), seuils de la 2067 (déplacements 15 000 €, réceptions 6 100 €, cadeaux 3 000 €), montants EDI.

## 10. Gérant majoritaire TNS (Caché_Provision_TNS, Caché_Driti_TNS, Caché_Driti_PAMC, Caché_Ecritures_TNS)

- Madelin au-delà du plafond = cotisations − plafond (si le plafond est renseigné).
- Revenu fiscal 1GB = rémunération + avantages en nature + Madelin au-delà du plafond + CSG/CRDS non déductible.
- Base « super brut » = PER + prévoyance + dividendes soumis + cotisations payées − remboursées + avantages en nature + rémunération ; abattement de 26 %, plancher 1,76 % du PASS, plafond 130 % du PASS ; base sociale = super brut − abattement.
- À provisionner : cotisations URSSAF (saisies d'après le simulateur) + formation professionnelle (0,25 % du PASS) + CSG/CRDS 9,7 % de la base (dont 6,8 % déductible).
- DRITI : DSCA = cotisations payées − CSG/CRDS appelée ; DSDA = remboursements ; DSEA = PER + prévoyance déductibles ; DSAA = dividendes soumis. PAMC : répartition au prorata des honoraires conventionnés.
- Écritures de provision au dernier jour du mois de clôture : 646200 / 438600 (cotisations), 644000 / 455000 (rémunération).

## 11. Déclaration de revenus (Récap_IR, IFU)

- BIC, LMP, LMNP = résultat fiscal si la case est « OUI ». Revenus en 5KC, 5NC, 5NA ; déficits en 5KF, 5NF, 5NY.
- Indemnité d'occupation : 4BE (revenus fonciers), 5ND (micro-LMNP, *correction n°3*).
- IFU : cases 2DC, 2CG, 2BH et 2CK de l'associé choisi, d'après la répartition de l'AG.

## 12. Cadrage social (Cadrage_Social_SILAE)

Journal de paie importé. Brut = ligne « Brut » ; avantages en nature = rubriques A…​.b positives ; indemnités de rupture = rubriques J… ; cotisations patronales regroupées par organisme selon les deux premières lettres du code (AA retraite ; CH, SS URSSAF ; PR, PS, PX prévoyance et mutuelle ; TC formation et apprentissage ; TR titres-restaurant). Chaque total est rapproché du montant comptable saisi.

## 13. Chiffres clés et mail (Mail_bilan)

CA, marge globale (hors production immobilisée), charges de personnel, EBITDA, RCAI, IS, résultat, trésorerie (512), autres disponibilités, stocks, clients, fournisseurs, TVA (44567, 44583, 44551), BFR, IS (444), capitaux propres. Échéances : IS et CA12 au 15 mai N+1 pour une clôture en décembre (sinon clôture + 15 jours + 3 mois), flat tax le 15 du mois qui suit le paiement des dividendes.
