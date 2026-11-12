/* Dossier Bilan : l'interface. Une page, sans dépendance externe.
   Principe : le serveur renvoie le dossier ENTIÈREMENT recalculé à chaque saisie (quelques millisecondes) ; l'écran
   est redessiné à partir de ce résultat. Les cellules ambrées (classe « s ») sont des saisies, le reste est calculé. */
"use strict";

const E = { moi: null, statuts: [], route: [], dossier: null, onglet: "synthese", sous: {}, filtre: "", masquer: false, ouverts: {}, file: [], envoi: null };
const $ = (s, r = document) => r.querySelector(s);
const NF = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const NF0 = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const PF = new Intl.NumberFormat("fr-FR", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });

function esc(v) { return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function eur(v, zero = "–") { if (v === null || v === undefined || v === "") return ""; if (typeof v !== "number") return esc(v); if (Math.abs(v) < 0.005) return zero; return `<span class="${v < 0 ? "neg" : ""}">${NF.format(v)}</span>`; }
function eur0(v) { return typeof v === "number" ? NF0.format(Math.abs(v) < 0.5 ? 0 : v) + " €" : esc(v); }
function pct(v) { return typeof v === "number" ? (Math.abs(v) < 0.0005 ? "–" : PF.format(v)) : ""; }
function dateFr(iso) { if (!iso) return ""; const [a, m, j] = String(iso).slice(0, 10).split("-"); return j ? `${j}/${m}/${a}` : iso; }
function nombreFr(s) { if (s === null || s === undefined) return null; s = String(s).trim().replace(/\s| |€/g, ""); if (s === "" || s === "-") return null;
  if (s.includes(",") && s.includes(".")) s = s.replace(/\./g, "").replace(",", "."); else s = s.replace(",", "."); const n = Number(s); return Number.isFinite(n) ? n : NaN; }
function ic(nom) { return `<svg class="ic"><use href="#i-${nom}"/></svg>`; }
function get(o, chemin) { return chemin.split(".").reduce((x, k) => (x == null ? undefined : x[k]), o); }

const ICONES = {
  dossiers: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  reglages: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  lune: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>', fleche: '<path d="M15 18l-6-6 6-6"/>', telecharger: '<path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14"/>',
  importer: '<path d="M12 21V9m0 0l-4 4m4-4l4 4M5 3h14"/>', nuage: '<path d="M7 18a5 5 0 1 1 .9-9.9A6 6 0 0 1 19 9a4.5 4.5 0 0 1-1 9z"/>',
  sortie: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>', copier: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  impression: '<path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v7H6z"/>',
};
function sprite() { return `<svg width="0" height="0" style="position:absolute">${Object.entries(ICONES).map(([k, v]) => `<symbol id="i-${k}" viewBox="0 0 24 24">${v}</symbol>`).join("")}</svg>`; }

// ---------------------------------------------------------------------------------------------------------------
// Serveur
// ---------------------------------------------------------------------------------------------------------------
async function api(methode, url, corps, formulaire) {
  const opts = { method: methode, headers: { "X-Bilan": "1" } };
  if (formulaire) opts.body = formulaire;
  else if (corps !== undefined) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(corps); }
  const r = await fetch(url, opts);
  let d = {};
  try { d = await r.json(); } catch (_) { /* réponse vide */ }
  if (r.status === 401 && url !== "/api/connexion") { E.moi = null; afficherConnexion(); throw new Error(d.erreur || "Session expirée."); }
  if (!r.ok) { const e = new Error(d.erreur || `Erreur ${r.status}`); e.champs = d.champs; e.conflit = d.conflit; throw e; }
  return d;
}
function toast(msg, erreur = false) {
  const t = document.createElement("div"); t.className = "toast" + (erreur ? " erreur" : ""); t.textContent = msg;
  $("#toasts").appendChild(t); setTimeout(() => t.remove(), erreur ? 7000 : 3500);
}

// ---------------------------------------------------------------------------------------------------------------
// Connexion et coque
// ---------------------------------------------------------------------------------------------------------------
async function afficherConnexion(message = "") {
  let cfg = {};
  try { cfg = await (await fetch("/api/config")).json(); } catch (_) { /* serveur injoignable : formulaire classique */ }
  if (cfg.demo) {
    // Démo hors ligne : connexion automatique au compte « demo » (sauf juste après une déconnexion volontaire)
    if (!E.sorti) {
      try { await api("POST", "/api/connexion", { identifiant: "demo", mot_de_passe: "demo" }); demarrer(); return; } catch (_) { /* écran ci-dessous */ }
    }
    $("#app").innerHTML = `${sprite()}<div id="connexion"><div class="carte-connexion"><div class="logo"><img src="logo.svg" alt=""></div><h1>Dossier Bilan</h1><p>Dossiers de travail de clôture</p>
      <div class="bandeau-demo"><b>Mode démo</b> : dossiers fictifs, aucun service externe. Compte <b>demo</b>, mot de passe <b>demo</b>.</div>
      <button class="btn primaire" id="entrer-demo" style="width:100%;justify-content:center">Entrer dans la démo</button><div id="err-connexion"></div></div></div>`;
    $("#entrer-demo").onclick = async () => {
      try { E.sorti = false; await api("POST", "/api/connexion", { identifiant: "demo", mot_de_passe: "demo" }); demarrer(); }
      catch (e) { $("#err-connexion").innerHTML = `<div class="message-erreur">${esc(e.message)}</div>`; }
    };
    return;
  }
  if (cfg.sans_mdp) {
    $("#app").innerHTML = `${sprite()}<div id="connexion"><div class="carte-connexion"><div class="logo"><img src="logo.svg" alt=""></div><h1>Dossier Bilan</h1><p>Qui êtes-vous ?</p>
      ${cfg.comptes.map(c => `<button class="btn primaire" data-qui="${esc(c.identifiant)}" style="width:100%;justify-content:center;margin-top:8px">${esc(c.nom)}</button>`).join("")}<div id="err-connexion"></div></div></div>`;
    document.querySelectorAll("[data-qui]").forEach(b => b.onclick = async () => {
      try { await api("POST", "/api/connexion", { identifiant: b.dataset.qui }); demarrer(); }
      catch (e) { $("#err-connexion").innerHTML = `<div class="message-erreur">${esc(e.message)}</div>`; }
    });
    return;
  }
  $("#app").innerHTML = `${sprite()}<div id="connexion"><form class="carte-connexion" id="f-connexion">
    <div class="logo"><img src="logo.svg" alt=""></div><h1>Dossier Bilan</h1><p>Dossiers de travail de clôture</p>
    <label>Identifiant</label><input class="champ" name="identifiant" autocomplete="username" autofocus>
    <label>Mot de passe</label><input class="champ" name="mot_de_passe" type="password" autocomplete="current-password">
    ${message ? `<div class="message-erreur">${esc(message)}</div>` : ""}<div id="err-connexion"></div>
    <button class="btn primaire" style="width:100%;margin-top:16px;justify-content:center">Se connecter</button></form></div>`;
  $("#f-connexion").onsubmit = async ev => {
    ev.preventDefault();
    const f = new FormData(ev.target);
    try { await api("POST", "/api/connexion", { identifiant: f.get("identifiant"), mot_de_passe: f.get("mot_de_passe") }); demarrer(); }
    catch (e) { $("#err-connexion").innerHTML = `<div class="message-erreur">${esc(e.message)}</div>`; }
  };
}

function coque() {
  const ini = (E.moi.nom || "?").split(" ").map(x => x[0]).join("").slice(0, 2).toUpperCase();
  $("#app").innerHTML = `${sprite()}<div id="coque"><nav id="gauche"><div class="logo"><img src="logo.svg" alt="Dossier Bilan"></div>
    <div class="rail"><button data-nav="dossiers" data-titre="Dossiers">${ic("dossiers")}</button><button data-nav="parametres" data-titre="Paramètres">${ic("reglages")}</button></div>
    <div class="bas-rail"><button class="rond" id="theme" title="Thème clair / sombre">${ic("lune")}</button>
    <button class="avatar" id="sortie" title="${E.moi.sans_mdp ? "Changer d'utilisateur" : "Se déconnecter"} (${esc(E.moi.nom)})">${esc(ini)}</button></div></nav><main id="droite"></main></div>`;
  document.querySelectorAll("[data-nav]").forEach(b => b.onclick = () => aller("#/" + b.dataset.nav));
  $("#theme").onclick = () => { const t = document.documentElement.dataset.theme === "sombre" ? "clair" : "sombre"; document.documentElement.dataset.theme = t; try { localStorage.setItem("theme", t); } catch (_) {} };
  $("#sortie").onclick = async () => { await api("POST", "/api/deconnexion"); E.moi = null; E.sorti = true; afficherConnexion(); };
}

async function demarrer() {
  try { const m = await api("GET", "/api/moi"); E.moi = m; E.statuts = m.statuts; } catch (_) { afficherConnexion(); return; }
  coque(); router();
}
function aller(h) { if (location.hash === h) router(); else location.hash = h; }
window.addEventListener("hashchange", () => { if (E.moi) router(); });

async function router() {
  const p = (location.hash || "#/dossiers").slice(2).split("/");
  document.querySelectorAll("[data-nav]").forEach(b => b.classList.toggle("actif", b.dataset.nav === (p[0] === "dossier" ? "dossiers" : p[0])));
  if (p[0] === "dossier" && p[1]) { E.onglet = p[2] || "synthese"; await ouvrirDossier(+p[1]); }
  else if (p[0] === "parametres") pageParametres();
  else pageDossiers();
}

// ---------------------------------------------------------------------------------------------------------------
// Liste des dossiers
// ---------------------------------------------------------------------------------------------------------------
async function pageDossiers() {
  E.dossier = null;
  const d = $("#droite");
  d.innerHTML = `<div class="entete"><div><h1>Dossiers bilan${E.moi.demo ? '<span class="badge-demo">Démo</span>' : ""}</h1><div class="sous">Un dossier par client et par exercice${E.moi.demo ? " · dossiers fictifs, chiffres inventés" : ""}</div></div>
    <div class="outils"><button class="btn primaire" id="nouveau">${ic("plus")} Nouveau dossier</button></div></div>
    <div class="barre"><input class="champ" id="recherche" placeholder="Rechercher un client…" value="${esc(E.filtreDossiers || "")}"></div>
    <div class="zone"><div class="carte" style="padding:0"><table class="t"><thead><tr><th>Client</th><th>Exercice</th><th>Balance</th><th>Dernière modification</th></tr></thead>
    <tbody id="liste"><tr><td colspan="4" class="vide">Chargement…</td></tr></tbody></table></div></div>`;
  $("#nouveau").onclick = () => fenetreNouveau();
  let dossiers = [];
  try { dossiers = (await api("GET", "/api/dossiers")).dossiers; } catch (e) { toast(e.message, true); }
  E.listeDossiers = dossiers;
  const dessiner = () => {
    const q = ($("#recherche").value || "").toLowerCase(); E.filtreDossiers = q;
    const l = dossiers.filter(x => !q || x.nom.toLowerCase().includes(q));
    $("#liste").innerHTML = l.length ? l.map(x => `<tr class="ligne-dossier" data-id="${x.id}"><td>${esc(x.nom)}</td>
      <td>${dateFr(x.debut_exercice)} → ${dateFr(x.cloture)}</td>
      <td>${x.source_balance ? `<span class="pastille ${x.source_balance === "Pennylane" ? "bleu" : "neutre"}">${esc(x.source_balance)}</span> <span class="note">${dateFr(x.balance_importee_le)}</span>` : '<span class="pastille alerte">À importer</span>'}</td>
      <td class="note">${dateFr(x.maj_le)} ${esc((x.maj_le || "").slice(11, 16))} · ${esc(x.maj_par || "")}</td></tr>`).join("")
      : `<tr><td colspan="4" class="vide">${dossiers.length ? "Aucun dossier ne correspond." : "Aucun dossier. Créez le premier avec « Nouveau dossier »."}</td></tr>`;
    document.querySelectorAll(".ligne-dossier").forEach(tr => tr.onclick = () => aller(`#/dossier/${tr.dataset.id}/synthese`));
  };
  $("#recherche").oninput = dessiner; dessiner();
}

function fenetre(html, init) {
  const v = document.createElement("div"); v.className = "voile"; v.innerHTML = `<div class="fenetre">${html}</div>`;
  document.body.appendChild(v);
  const fermer = () => v.remove();
  v.addEventListener("mousedown", e => { if (e.target === v) fermer(); });
  document.addEventListener("keydown", function esc_(e) { if (e.key === "Escape") { fermer(); document.removeEventListener("keydown", esc_); } });
  v.querySelectorAll("[data-fermer]").forEach(b => b.onclick = fermer);
  if (init) init(v, fermer);
  return v;
}

function fenetreNouveau() {
  const precedents = (E.listeDossiers || []).map(x => `<option value="${x.id}">${esc(x.nom)} (clôture ${dateFr(x.cloture)})</option>`).join("");
  fenetre(`<h2>Nouveau dossier bilan</h2>
    <div class="sous-onglets"><button class="actif" data-mode="pennylane">${ic("nuage")} Depuis Pennylane</button><button data-mode="manuel">Saisie manuelle</button></div>
    <div data-panneau="pennylane"><input class="champ" id="pl-q" placeholder="Filtrer les dossiers du cabinet…">
      <div class="note" id="pl-compte" style="margin-top:6px"></div>
      <div class="liste-choix" id="pl-liste" style="max-height:320px"><div class="note" style="cursor:default">Chargement des dossiers du cabinet depuis Pennylane…</div></div>
      <div id="pl-ex" style="margin-top:10px"></div></div>
    <div data-panneau="manuel" class="cache"><div class="grille-form">
      <div><label>Nom du client</label><input class="champ" id="m-nom"></div><div><label>Forme</label><input class="champ" id="m-forme" placeholder="SAS, SARL…"></div>
      <div><label>Début d'exercice</label><input class="champ" id="m-debut" type="date"></div><div><label>Clôture</label><input class="champ" id="m-cloture" type="date"></div></div>
      <p class="note">La balance s'importe ensuite depuis un fichier (Excel ou CSV).</p></div>
    <div style="margin-top:12px"><label class="note">Reprendre les statuts, commentaires et associés d'un exercice précédent (facultatif)</label>
      <select class="champ" id="reprise"><option value="">Non</option>${precedents}</select></div>
    <div id="nv-err"></div>
    <div class="actions"><button class="btn" data-fermer>Annuler</button><button class="btn primaire" id="nv-ok">Créer le dossier</button></div>`, (v, fermer) => {
    let mode = "pennylane", choix = null, exercices = [];
    if (E.moi.demo) {  // démo : pas de Pennylane, saisie manuelle seulement
      mode = "manuel"; v.querySelector('[data-mode="pennylane"]').disabled = true; v.querySelector('[data-mode="pennylane"]').title = "Désactivé en mode démo";
      v.querySelectorAll("[data-mode]").forEach(x => x.classList.toggle("actif", x.dataset.mode === "manuel"));
      v.querySelectorAll("[data-panneau]").forEach(p => p.classList.toggle("cache", p.dataset.panneau !== "manuel"));
    }
    v.querySelectorAll("[data-mode]").forEach(b => b.onclick = () => {
      mode = b.dataset.mode; v.querySelectorAll("[data-mode]").forEach(x => x.classList.toggle("actif", x === b));
      v.querySelectorAll("[data-panneau]").forEach(p => p.classList.toggle("cache", p.dataset.panneau !== mode));
    });
    // Tous les dossiers du portefeuille, chargés à l'ouverture ; la saisie ne fait que filtrer la liste
    const existants = new Map((E.listeDossiers || []).filter(x => x.pennylane_id).map(x => [String(x.pennylane_id), x]));
    let tous = [];
    const dessinerListe = () => {
      const q = $("#pl-q", v).value.trim().toLowerCase();
      const l = tous.filter(x => !q || x.nom.toLowerCase().includes(q) || String(x.siren).includes(q));
      $("#pl-compte", v).textContent = `${l.length} dossier(s) sur ${tous.length}`;
      $("#pl-liste", v).innerHTML = l.length ? l.map(x => { const deja = existants.get(String(x.id));
        return `<div data-id="${esc(x.id)}" data-nom="${esc(x.nom)}" data-siren="${esc(x.siren)}" class="${choix && String(choix.id) === String(x.id) ? "choisi" : ""}">${esc(x.nom)} <span class="note">${esc(x.siren)}</span>${deja ? ` <span class="pastille neutre">bilan au ${dateFr(deja.cloture)}</span>` : ""}</div>`; }).join("")
        : '<div class="note">Aucun dossier ne correspond.</div>';
      v.querySelectorAll("#pl-liste [data-id]").forEach(el => el.onclick = () => choisir(el));
    };
    async function choisir(el) {
      v.querySelectorAll("#pl-liste [data-id]").forEach(x => x.classList.toggle("choisi", x === el));
      choix = { id: el.dataset.id, nom: el.dataset.nom, siren: el.dataset.siren };
      const deja = existants.get(String(choix.id));
      if (deja) $("#reprise", v).value = String(deja.id);  // exercice précédent du même client : reprise proposée d'office
      $("#pl-ex", v).innerHTML = '<span class="note">Lecture des exercices…</span>';
      try {
        exercices = (await api("GET", "/api/pennylane/exercices?company_id=" + encodeURIComponent(choix.id))).exercices;
        $("#pl-ex", v).innerHTML = exercices.length ? `<label class="note">Exercice</label><select class="champ" id="pl-exo">${exercices.map((e, i) => `<option value="${i}">${dateFr(e.debut)} → ${dateFr(e.fin)}</option>`).join("")}</select>`
          : '<div class="message-erreur">Aucun exercice dans Pennylane pour ce dossier.</div>';
      } catch (e) { $("#pl-ex", v).innerHTML = `<div class="message-erreur">${esc(e.message)}</div>`; }
    }
    $("#pl-q", v).oninput = dessinerListe;
    if (!E.moi.demo) api("GET", "/api/pennylane/dossiers").then(r => { tous = r.dossiers; dessinerListe(); $("#pl-q", v).focus(); })
      .catch(e => { $("#pl-liste", v).innerHTML = `<div class="message-erreur" style="margin:8px">${esc(e.message)}<br><a href="#/parametres">Paramètres › Pennylane</a></div>`; });
    $("#nv-ok", v).onclick = async () => {
      const reprendre = $("#reprise", v).value || null;
      let corps;
      if (mode === "pennylane") {
        if (!choix || !$("#pl-exo", v)) { $("#nv-err", v).innerHTML = '<div class="message-erreur">Choisissez le dossier et l\'exercice.</div>'; return; }
        const e = exercices[+$("#pl-exo", v).value];
        corps = { nom: choix.nom, siren: choix.siren, pennylane_id: choix.id, debut_exercice: e.debut, cloture: e.fin, reprendre_de: reprendre };
      } else {
        corps = { nom: $("#m-nom", v).value, forme: $("#m-forme", v).value, debut_exercice: $("#m-debut", v).value, cloture: $("#m-cloture", v).value, reprendre_de: reprendre };
      }
      $("#nv-ok", v).disabled = true;
      try {
        const r = await api("POST", "/api/dossiers", corps);
        fermer(); aller(`#/dossier/${r.id}/synthese`);
        if (mode === "pennylane") setTimeout(() => importerPennylane(), 400);
      } catch (e) {
        $("#nv-ok", v).disabled = false;
        $("#nv-err", v).innerHTML = `<div class="message-erreur">${esc(e.champs ? Object.values(e.champs).join(" ") : e.message)}</div>`;
      }
    };
  });
}

// ---------------------------------------------------------------------------------------------------------------
// Dossier : chargement, enregistrement des saisies
// ---------------------------------------------------------------------------------------------------------------
async function ouvrirDossier(id) {
  if (!E.dossier || E.dossier.dossier.id !== id) {
    $("#droite").innerHTML = '<div class="vide">Calcul du dossier…</div>';
    try { E.dossier = await api("GET", `/api/dossiers/${id}`); } catch (e) { toast(e.message, true); aller("#/dossiers"); return; }
  }
  dessinerDossier();
}

function recevoir(d) { E.dossier = d; dessinerDossier(true); }

// Les saisies partent par lots (une frappe rapide sur plusieurs cellules = un seul aller-retour)
function saisir(chemin, valeur) {
  E.file = E.file.filter(c => c.chemin !== chemin); E.file.push({ chemin, valeur });
  clearTimeout(E.minuterie); E.minuterie = setTimeout(envoyer, 250);
  const st = $("#etat-enregistrement"); if (st) st.textContent = "Enregistrement…";
}
async function envoyer() {
  if (E.envoi) { E.minuterie = setTimeout(envoyer, 150); return; }
  if (!E.file.length || !E.dossier) return;
  const lot = E.file; E.file = [];
  const id = E.dossier.dossier.id;
  E.envoi = api("PATCH", `/api/dossiers/${id}`, { version: E.dossier.dossier.version, changements: lot });
  try { const d = await E.envoi; if (E.dossier && E.dossier.dossier.id === id) recevoir(d); }
  catch (e) {
    toast(e.message, true);
    if (e.conflit) { E.dossier = await api("GET", `/api/dossiers/${id}`); dessinerDossier(true); }
  } finally { E.envoi = null; }
}

function lireSaisie(el) {
  if (el.type === "checkbox") return el.checked;
  if (el.dataset.type === "nombre") {
    const n = nombreFr(el.value);
    if (Number.isNaN(n)) { toast(`« ${el.value} » n'est pas un montant.`, true); return undefined; }
    return n;
  }
  return el.value;
}

// Champs de saisie (valeur actuelle tirée des saisies du dossier)
function valeurSaisie(chemin) { return get({ saisies: E.dossier.saisies, infos: E.dossier.infos, dossier: E.dossier.dossier, parametres: E.dossier.parametres }, chemin); }
function sN(chemin, opts = {}) {
  const v = valeurSaisie(chemin);
  const aff = (v === null || v === undefined || v === "") ? "" : (typeof v === "number" ? String(v).replace(".", ",") : v);
  return `<input class="s" data-c="${esc(chemin)}" data-type="nombre" value="${esc(aff)}" placeholder="${esc(opts.ph ?? "")}" ${opts.style ? `style="${opts.style}"` : ""}>`;
}
function sT(chemin, opts = {}) { const v = valeurSaisie(chemin) ?? opts.defaut ?? ""; return `<input class="s t" data-c="${esc(chemin)}" value="${esc(v)}" placeholder="${esc(opts.ph ?? "")}" ${opts.type ? `type="${opts.type}"` : ""}>`; }
function sZ(chemin, ph = "") { return `<textarea class="s" data-c="${esc(chemin)}" placeholder="${esc(ph)}">${esc(valeurSaisie(chemin) ?? "")}</textarea>`; }
function sS(chemin, options, defaut = "") {
  const v = valeurSaisie(chemin) ?? defaut;
  return `<select class="s" data-c="${esc(chemin)}">${options.map(o => { const [val, lib] = Array.isArray(o) ? o : [o, o || "—"]; return `<option value="${esc(val)}" ${String(val) === String(v) ? "selected" : ""}>${esc(lib)}</option>`; }).join("")}</select>`;
}
function sC(chemin, defaut = false) { const v = valeurSaisie(chemin); return `<input type="checkbox" data-c="${esc(chemin)}" ${(v ?? defaut) ? "checked" : ""}>`; }

// ---------------------------------------------------------------------------------------------------------------
// Dossier : en-tête, onglets
// ---------------------------------------------------------------------------------------------------------------
const ONGLETS = [
  ["synthese", "Synthèse"], ["balance", "Balance"], ["revision", "Révision"], ["sig", "SIG"], ["capitaux", "Capitaux et AG"],
  ["ca_tva", "CA et TVA"], ["fiscal", "Fiscal et liasse"], ["tns", "Gérant TNS"], ["ir", "Déclaration IR"], ["social", "Social"],
  ["questionnaires", "Questionnaires"], ["mail", "Mail bilan"], ["infos", "Dossier"],
];

function dessinerDossier(apresSaisie = false) {
  const d = E.dossier, r = d.resultats, m = d.dossier;
  // Garder le curseur dans la cellule en cours de saisie après le redessin
  const actif = document.activeElement, cle = actif && actif.dataset ? actif.dataset.c : null;
  const selection = actif && "selectionStart" in actif ? [actif.selectionStart, actif.selectionEnd] : null;
  const defil = $(".zone") ? $(".zone").scrollTop : 0;
  const alertes = r.controles.filter(c => c.niveau !== "ok").length;
  $("#droite").innerHTML = `<div class="entete"><div><button class="retour" id="b-retour">${ic("fleche")} Dossiers</button>
      <h1>${esc(m.nom)}${E.moi.demo ? '<span class="badge-demo">Démo</span>' : ""}</h1><div class="sous">Exercice du ${dateFr(m.debut_exercice)} au ${dateFr(m.cloture)} · ${m.source_balance ? esc(m.source_balance) + " le " + dateFr(m.balance_importee_le) : "balance à importer"}</div></div>
    <div class="outils"><span id="etat-enregistrement">Calculé en ${d.calcul_ms} ms</span>
      <button class="btn" id="b-import">${ic("importer")} Importer la balance</button>
      <a class="btn" href="/api/dossiers/${m.id}/export.xlsx">${ic("telecharger")} Export Excel</a>
      <button class="btn" id="b-imprimer" title="Imprimer l'onglet">${ic("impression")}</button></div></div>
    <div class="onglets">${ONGLETS.map(([k, l]) => `<button data-onglet="${k}" class="${E.onglet === k ? "actif" : ""}">${l}${k === "synthese" && alertes ? ` <span class="compteur">${alertes}</span>` : ""}</button>`).join("")}</div>
    <div class="zone" id="zone">${(VUES[E.onglet] || VUES.synthese)(r, d)}</div>`;
  document.querySelectorAll("[data-onglet]").forEach(b => b.onclick = () => aller(`#/dossier/${m.id}/${b.dataset.onglet}`));
  $("#b-import").onclick = fenetreImport;
  $("#b-retour").onclick = () => aller("#/dossiers");
  $("#b-imprimer").onclick = () => window.print();
  brancher($("#zone"));
  if (E.onglet === "ca_tva" && E.sous.ca_tva === "recap") chargerComptazap();
  if (apresSaisie) { $(".zone").scrollTop = defil; }
  if (cle) {
    const el = document.querySelector(`[data-c="${CSS.escape(cle)}"]`);
    if (el && el !== actif) { el.focus(); if (selection && el.setSelectionRange && el.type !== "checkbox") try { el.setSelectionRange(...selection); } catch (_) {} }
  }
}

function brancher(zone) {
  zone.querySelectorAll("[data-c]").forEach(el => {
    const ev = el.tagName === "SELECT" || el.type === "checkbox" ? "change" : "change";
    el.addEventListener(ev, () => { const v = lireSaisie(el); if (v !== undefined) saisir(el.dataset.c, v); });
    if (el.tagName === "INPUT" && el.type !== "checkbox") el.addEventListener("keydown", e => {
      if (e.key === "Enter") { e.preventDefault(); el.dispatchEvent(new Event("change")); suivant(el, e.shiftKey ? -1 : 1); }
    });
  });
  zone.querySelectorAll("[data-sous]").forEach(b => b.onclick = () => { E.sous[E.onglet] = b.dataset.sous; dessinerDossier(true); });
  zone.querySelectorAll("[data-ouvrir]").forEach(b => b.onclick = () => { E.ouverts[b.dataset.ouvrir] = !E.ouverts[b.dataset.ouvrir]; dessinerDossier(true); });
  zone.querySelectorAll("[data-aller]").forEach(b => b.onclick = () => aller(`#/dossier/${E.dossier.dossier.id}/${b.dataset.aller}`));
  zone.querySelectorAll("[data-action]").forEach(b => b.onclick = () => ACTIONS[b.dataset.action](b));
  const f = zone.querySelector("#filtre-balance");
  if (f) f.oninput = () => { E.filtre = f.value; filtrerBalance(); };
}
function suivant(el, sens) {
  const champs = [...document.querySelectorAll("#zone input.s, #zone select.s")];
  const i = champs.indexOf(el); const n = champs[i + sens]; if (n) { n.focus(); n.select && n.select(); }
}

// ---------------------------------------------------------------------------------------------------------------
// Les vues du dossier
// ---------------------------------------------------------------------------------------------------------------
const VUES = {};

VUES.synthese = (r, d) => {
  const n = r.sig.n, n1 = r.sig.n1, cap = r.capitaux.continuite_n;
  const kpi = (l, v, v1, f = eur0) => `<div class="kpi"><div class="l">${l}</div><div class="v">${f(v)}</div><div class="d">${v1 === null ? "&nbsp;" : "N-1 : " + f(v1)}</div></div>`;
  const vide = !r.balance.lignes.length;
  return `${vide ? `<div class="carte"><h2>Première étape : importer la balance</h2><p>La balance N et N-1 vient de Pennylane (dossier relié) ou d'un fichier Excel / CSV.</p>
      <button class="btn primaire" data-action="import">${ic("importer")} Importer la balance</button></div>` : ""}
    <div class="kpis">${kpi("Chiffre d'affaires", n.ca, n1.ca)}${kpi("Valeur ajoutée", n.valeur_ajoutee, n1.valeur_ajoutee)}${kpi("EBE", n.ebe, n1.ebe)}
      ${kpi("Résultat de l'exercice", r.balance.resultat_n, r.balance.resultat_n1)}${kpi("IS calculé", r.fiscal.is_total, null, v => v === null ? "" : eur0(v))}
      ${kpi("Capitaux propres", cap.total, r.capitaux.continuite_n1.total)}</div>
    <div class="deux"><div class="carte"><h2>Contrôles du dossier</h2>${r.controles.map(c => `<div class="controle"><span class="pastille ${c.niveau}">${{ ok: "OK", alerte: "À voir", erreur: "Erreur" }[c.niveau]}</span>
        <div><div class="titre">${esc(c.titre)}</div>${c.niveau !== "ok" && c.detail ? `<div class="detail">${esc(c.detail)}</div>` : ""}</div>
        ${c.feuille && c.niveau !== "ok" ? `<button class="btn petit" data-aller="${c.feuille === "import" ? "synthese" : c.feuille === "balance" ? "balance" : c.feuille === "tva" ? "ca_tva" : c.feuille === "cadrage_ca" ? "ca_tva" : c.feuille}">Voir</button>` : ""}</div>`).join("")}</div>
      <div class="carte"><h2>Avancement de la révision</h2><table class="t"><thead><tr><th>Cycle</th><th class="n">Comptes</th><th class="n">Validés</th><th class="n">Solde N</th></tr></thead><tbody>
        ${r.cycles.map(c => `<tr><td>${esc(c.titre)}</td><td class="n">${c.lignes.length}</td><td class="n">${c.lignes.length ? `<span class="pastille ${c.valides === c.lignes.length ? "ok" : c.valides ? "alerte" : "neutre"}">${c.valides} / ${c.lignes.length}</span>` : "–"}</td><td class="n">${eur(c.total_n)}</td></tr>`).join("")}
        </tbody></table>
        <h3>Questionnaires</h3>${Object.entries({ lab: "Acceptation / maintien", revision: "Révision", bouclage: "Bouclage" }).map(([k, l]) => { const a = r.questionnaires[k].avancement; return `<div class="controle"><div class="titre">${l}</div><span class="pastille ${a.fait === a.total ? "ok" : "neutre"}" style="margin-left:auto">${a.fait} / ${a.total}</span></div>`; }).join("")}
      </div></div>`;
};

function filtrerBalance() {
  const q = E.filtre.toLowerCase();
  document.querySelectorAll("#t-balance tbody tr").forEach(tr => {
    const ok = (!q || tr.dataset.cle.includes(q)) && (!E.masquer || tr.dataset.mvt === "1");
    tr.style.display = ok ? "" : "none";
  });
}
VUES.balance = r => {
  const b = r.balance;
  const ok = Math.abs(b.total_n) < 0.005 && Math.abs(b.total_n1) < 0.005;
  setTimeout(filtrerBalance);
  return `<div class="carte"><h2>Balance comparative <span class="aide">${b.lignes.length} comptes · ${esc(b.libelle_n)} : ${eur0(b.resultat_n)} · ${esc(b.libelle_n1)} : ${eur0(b.resultat_n1)}
      · <span class="pastille ${ok ? "ok" : "erreur"}">${ok ? "Équilibrée" : "Déséquilibrée"}</span></span></h2>
    <div class="barre"><input class="champ" id="filtre-balance" placeholder="Filtrer : numéro, libellé, rubrique…" value="${esc(E.filtre)}">
      <label class="note"><input type="checkbox" id="masquer" ${E.masquer ? "checked" : ""}> Masquer les comptes soldés et non mouvementés</label></div>
    <div class="defile"><table class="t" id="t-balance"><thead><tr><th>Compte</th><th>Libellé</th><th class="n">Solde N</th><th class="n">Solde N-1</th><th class="n">Variation</th><th class="n">Var. %</th><th>Rubrique SIG</th><th style="min-width:220px">Commentaire</th></tr></thead>
    <tbody>${b.lignes.map(l => `<tr data-cle="${esc((l.compte + " " + l.libelle + " " + (l.sig || "")).toLowerCase())}" data-mvt="${l.mouvemente ? 1 : 0}"><td class="compte">${esc(l.compte)}</td><td class="lib" title="${esc(l.libelle)}">${esc(l.libelle)}</td>
      <td class="n">${eur(l.n)}</td><td class="n">${eur(l.n1)}</td><td class="n">${eur(l.var)}</td><td class="n">${pct(l.var_pct)}</td><td class="note">${esc((l.sig || "").trim())}</td>
      <td>${sT("saisies.commentaires." + l.compte)}</td></tr>`).join("")}</tbody>
    <tfoot><tr class="total"><td colspan="2">Total (doit être nul)</td><td class="n">${eur(b.total_n, "0,00")}</td><td class="n">${eur(b.total_n1, "0,00")}</td><td colspan="4"></td></tr></tfoot></table></div></div>`;
};
document.addEventListener("change", e => { if (e.target.id === "masquer") { E.masquer = e.target.checked; filtrerBalance(); } });

VUES.revision = r => {
  const cle = E.sous.revision || r.cycles.find(c => c.lignes.length)?.cle || "attente";
  const cy = r.cycles.find(c => c.cle === cle);
  return `<div class="sous-onglets">${r.cycles.map(c => `<button data-sous="${c.cle}" class="${c.cle === cle ? "actif" : ""}">${esc(c.titre)}<small>${c.valides}/${c.lignes.length}</small></button>`).join("")}</div>
    <div class="carte"><h2>${esc(cy.titre)} <span class="aide">Comptes ${esc(cy.racines)}</span></h2>
    ${cy.lignes.length ? `<div class="defile"><table class="t"><thead><tr><th>Compte</th><th>Libellé</th><th class="n">Solde N</th><th class="n">Solde N-1</th><th class="n">Variation</th><th style="width:150px">Statut</th><th style="min-width:260px">Commentaire de révision</th></tr></thead><tbody>
      ${cy.lignes.map(l => `<tr><td class="compte">${esc(l.compte)}</td><td class="lib" title="${esc(l.libelle)}">${esc(l.libelle)}</td><td class="n">${eur(l.n)}</td><td class="n">${eur(l.n1)}</td><td class="n">${eur(l.var)}</td>
        <td>${sS("saisies.revision." + l.compte + ".statut", E.statuts)}</td><td>${sT("saisies.revision." + l.compte + ".commentaire")}</td></tr>`).join("")}
      <tr class="total"><td colspan="2">Total</td><td class="n">${eur(cy.total_n)}</td><td class="n">${eur(cy.total_n1)}</td><td class="n">${eur(cy.total_n - cy.total_n1)}</td><td colspan="2"></td></tr></tbody></table></div>
      <div style="margin-top:10px"><button class="btn petit" data-action="tout-valider" data-cycle="${cy.cle}">Tout passer en « Validé »</button></div>` : '<div class="vide">Pas de compte dans ce cycle.</div>'}
    <h3>Observations générales</h3>${sZ("saisies.observations." + cy.cle, "Points relevés, demandes au client…")}</div>`;
};

VUES.sig = r => {
  const ligne = l => {
    const ouvert = E.ouverts["sig." + l.cle];
    const det = l.detail && l.detail.length;
    let h = `<tr class="${l.niveau ? "sous" : ""}"><td style="width:24px">${esc(l.signe)}</td><td>${det ? `<button class="lien" data-ouvrir="sig.${l.cle}">${ouvert ? "▾" : "▸"} ${esc(l.libelle)}</button>` : esc(l.libelle)}</td>
      <td class="n">${eur(l.n)}</td><td class="n">${pct(l.pct_n)}</td><td class="n">${eur(l.n1)}</td><td class="n">${pct(l.pct_n1)}</td><td class="n">${eur(l.var)}</td><td class="n">${pct(l.var_pct)}</td></tr>`;
    if (det && ouvert) h += l.detail.map(x => `<tr class="detail"><td></td><td>${esc(x.compte)} – ${esc(x.libelle)}</td><td class="n">${eur(x.n)}</td><td class="n">${pct(x.pct_n)}</td><td class="n">${eur(x.n1)}</td><td class="n">${pct(x.pct_n1)}</td><td class="n">${eur(x.var)}</td><td class="n">${pct(x.var_pct)}</td></tr>`).join("");
    return h;
  };
  const nr = r.sig.non_ranges;
  return `${nr.length ? `<div class="message-erreur">${nr.length} compte(s) de gestion hors SIG (racine absente du tableau des rubriques) : ${nr.map(x => esc(x.compte + " " + x.libelle)).join(", ")}. Ils manquent au résultat du SIG.</div>` : ""}
    <div class="carte"><h2>Soldes intermédiaires de gestion <span class="aide">Cliquez sur une rubrique pour voir ses comptes</span></h2>
    <table class="t"><thead><tr><th></th><th>Libellé</th><th class="n">N</th><th class="n">% CA</th><th class="n">N-1</th><th class="n">% CA</th><th class="n">Variation</th><th class="n">Var. %</th></tr></thead>
    <tbody>${r.sig.lignes.map(ligne).join("")}</tbody></table></div>`;
};

const ASSOC_CHAMPS_N1 = [["nom", "Nom de l'associé", "t"], ["qualite", "Qualité (PP, PM)", ["", "PP", "PM"]], ["dispense", "Dispense précompte IR", ["", "Dispensé"]],
  ["regime", "Régime du dividende", ["", "TNS", "NON TNS", "EI IS"]], ["parts", "Nombre de parts", "n"], ["force", "Dividende brut forcé", "n"]];
function tableAssocies(base, rep, avecQp) {
  const champs = [...ASSOC_CHAMPS_N1, avecQp ? ["qp", "QP capital + primes + CC moyen", "n"] : ["cc_moyen", "Compte courant moyen (TNS)", "n"]];
  const lignesCalc = [["pct", "% de détention", pct], ["affecte", "Dividende affecté au %", eur], ["retenu", "Dividende brut retenu (2DC)", eur],
    ...(avecQp ? [] : [["qp", "QP capital + primes + CC moyen", eur]]), ["base_ps", "Soumis aux prélèvements sociaux (2BH)", eur], ["base_cotis", "Soumis aux cotisations sociales (2CG)", eur],
    ["ps", "Prélèvements sociaux", eur], ["precompte", "Précompte IR 12,8 % (2CK)", eur], ["retenue", "Retenue à la source totale", eur], ["net", "Dividende net versé", eur],
    ["cotis_tns", "Cotisations TNS théoriques", eur], ["economie_is", "Économie d'IS", eur], ["cout", "Coût global pour l'entreprise", eur], ["cout_pct", "Coût en % du dividende", pct]];
  const n = rep.associes.length;
  let h = `<div class="defile" style="max-height:none"><table class="t"><thead><tr><th></th>${rep.associes.map((_, i) => `<th>Associé ${i + 1}</th>`).join("")}</tr></thead><tbody>`;
  for (const [k, l, t] of champs) h += `<tr><td>${l}</td>${Array.from({ length: n }, (_, i) => `<td>${Array.isArray(t) ? sS(`${base}.associes.${i}.${k}`, t) : t === "t" ? sT(`${base}.associes.${i}.${k}`, { ph: `Associé ${i + 1}` }) : sN(`${base}.associes.${i}.${k}`)}</td>`).join("")}</tr>`;
  for (const [k, l, f] of lignesCalc) h += `<tr><td>${l}</td>${rep.associes.map(a => `<td class="n">${f(a[k])}</td>`).join("")}</tr>`;
  return h + `</tbody></table></div>`;
}

VUES.capitaux = r => {
  const cap = r.capitaux, aff = cap.affectation, ag = r.ago_n, af = ag.affectation;
  const sous = E.sous.capitaux || "capitaux";
  const nav = `<div class="sous-onglets">${[["capitaux", "Capitaux propres"], ["ago_n1", "AG N-1 (dividendes votés)"], ["ago_n", "AG à tenir sur N"]].map(([k, l]) => `<button data-sous="${k}" class="${k === sous ? "actif" : ""}">${l}</button>`).join("")}</div>`;
  if (sous === "ago_n1") {
    return nav + `<div class="carte"><h2>Assemblée générale N-1 <span class="aide">Dividendes bruts à répartir : ${eur0(r.ago_n1.dividendes)} (saisis dans Capitaux propres)</span></h2>
      <div class="grille-form" style="max-width:300px"><div><label>Taux des prélèvements sociaux</label>${sN("saisies.ago_n1.taux_ps", { ph: "0,172" })}</div></div><br>
      ${tableAssocies("saisies.ago_n1", r.ago_n1, true)}
      <p class="note">Cotisations TNS sur la part des dividendes au-delà de 10 % : taux unique de ${pct(r.parametres.taux_cotis_tns_dividendes)} (onglet Dossier). L'Excel appliquait 25 % au 1er associé et 40 % aux autres.</p></div>`;
  }
  if (sous === "ago_n") {
    const rl = af.reserve_legale_calcul;
    return nav + `<div class="deux"><div class="carte"><h2>Situation avant et après l'assemblée</h2><table class="t"><thead><tr><th>Compte</th><th class="n">N-1</th><th class="n">N</th><th class="n">Variation AG</th><th class="n">Après AG</th></tr></thead><tbody>
        ${ag.lignes.map(l => `<tr><td>${esc(l.libelle)}</td><td class="n">${eur(l.n1)}</td><td class="n">${eur(l.n)}</td><td class="n">${eur(l.variation_ag)}</td><td class="n">${eur(l.apres_ag)}</td></tr>`).join("")}
        <tr><td>Résultat de l'exercice</td><td class="n">${eur(ag.situation_n1.resultat)}</td><td class="n">${eur(ag.situation_n.resultat)}</td><td class="n">${eur(-ag.situation_n.resultat)}</td><td class="n">–</td></tr>
        <tr class="total"><td>Capitaux propres totaux</td><td class="n">${eur(ag.situation_n1.total)}</td><td class="n">${eur(ag.situation_n.total)}</td><td class="n">${eur(ag.apres_ag.variation_total)}</td><td class="n">${eur(ag.apres_ag.total)}</td></tr>
        <tr><td>Rapportés au capital social</td><td class="n">${pct(ag.situation_n1.rapport)}</td><td class="n">${pct(ag.situation_n.rapport)}</td><td></td><td class="n">${pct(ag.apres_ag.rapport)}</td></tr></tbody></table></div>
      <div class="carte"><h2>Affectation du résultat N <span class="aide">${esc(af.libelle_resultat)} : ${eur0(r.balance.resultat_n)}</span></h2><table class="t"><tbody>
        <tr class="sous"><td>${esc(af.libelle_distribuable)}</td><td class="n">${eur(af.distribuable)}</td><td class="n note">Reste</td></tr>
        <tr><td>Réserve légale obligatoire <span class="pastille ${af.signal_reserve_legale === "Réserve à doter" ? "alerte" : "neutre"}">${esc(af.signal_reserve_legale || "—")}</span></td><td class="n">${eur(af.reserve_legale)}</td><td class="n">${eur(af.reste_progressif.reserve_legale)}</td></tr>
        <tr><td>Réserve statutaire</td><td>${sN("saisies.ago_n.reserve_statutaire")}</td><td class="n">${eur(af.reste_progressif.reserve_statutaire)}</td></tr>
        <tr><td>Réserves réglementées</td><td>${sN("saisies.ago_n.reserves_reglementees")}</td><td class="n">${eur(af.reste_progressif.reserves_reglementees)}</td></tr>
        <tr><td>Autres réserves</td><td>${sN("saisies.ago_n.autres_reserves")}</td><td class="n">${eur(af.reste_progressif.autres_reserves)}</td></tr>
        <tr><td>Dividendes bruts</td><td>${sN("saisies.ago_n.dividendes")}</td><td class="n">${eur(af.reste_progressif.dividendes)}</td></tr>
        <tr><td>Compte courant d'associé (société IR)</td><td>${sN("saisies.ago_n.compte_courant")}</td><td class="n">${eur(af.reste_progressif.compte_courant)}</td></tr>
        <tr><td>Report à nouveau créditeur</td><td class="n">${eur(af.ran_crediteur)}</td><td></td></tr><tr><td>Report à nouveau débiteur</td><td class="n">${eur(af.ran_debiteur)}</td><td></td></tr></tbody></table>
        <p class="note">Réserve légale : 10 % du capital = ${eur0(rl.theorique)} ; dotée ${eur0(rl.actuelle)} ; 5 % du résultat plafonné : ${eur0(rl.cinq_pourcent)}.</p></div></div>
      <div class="carte"><h2>Répartition des dividendes N</h2><div class="grille-form" style="max-width:640px"><div><label>Taux des prélèvements sociaux</label>${sN("saisies.ago_n.taux_ps", { ph: "0,186" })}</div><div><label>Date de paiement des dividendes</label>${sT("saisies.ago_n.date_paiement", { type: "date" })}</div></div><br>
        ${tableAssocies("saisies.ago_n", ag.repartition, false)}</div>`;
  }
  return nav + `<div class="deux"><div class="carte"><h2>Capitaux propres</h2><table class="t"><thead><tr><th>Compte</th><th class="n">Solde N-1</th><th class="n">Variation</th><th class="n">Solde N</th></tr></thead><tbody>
      ${cap.lignes.map(l => `<tr><td>${esc(l.libelle)} ${l.alerte ? `<span class="pastille alerte">${esc(l.alerte)}</span>` : ""}</td><td class="n">${eur(l.n1)}</td><td class="n">${eur(l.var)}</td><td class="n">${eur(l.n)}</td></tr>`).join("")}</tbody></table>
      <h3>Continuité d'exploitation</h3><table class="t"><thead><tr><th></th><th class="n">N-1</th><th class="n">N</th></tr></thead><tbody>
      ${[["hors_resultat", "Total capitaux propres hors résultat", eur], ["resultat", "Résultat", eur], ["total", "Capitaux propres totaux", eur], ["capital", "Capital social", eur], ["rapport", "Capitaux propres / capital social", pct]].map(([k, l, f]) => `<tr class="${k === "total" ? "total" : ""}"><td>${l}</td><td class="n">${f(cap.continuite_n1[k])}</td><td class="n">${f(cap.continuite_n[k])}</td></tr>`).join("")}</tbody></table>
      ${cap.continuite_n.rapport < 0.5 && cap.continuite_n.capital ? '<div class="message-erreur">Capitaux propres inférieurs à la moitié du capital social (art. L.223-42 / L.225-248 C. com.) : consultation des associés à prévoir.</div>' : ""}</div>
    <div class="carte"><h2>Compte rendu d'affectation du résultat N-1</h2><table class="t"><tbody>
      <tr class="sous"><td>${esc(aff.libelle_resultat)}</td><td class="n">${eur(aff.resultat_n1)}</td></tr>
      <tr><td>Affectation réserve légale</td><td class="n">${eur(aff.reserve_legale)}</td></tr><tr><td>Affectation réserve statutaire</td><td class="n">${eur(aff.reserve_statutaire)}</td></tr>
      <tr><td>Affectation réserves réglementées</td><td class="n">${eur(aff.reserves_reglementees)}</td></tr><tr><td>Affectation autres réserves</td><td class="n">${eur(aff.autres_reserves)}</td></tr>
      <tr><td>Affectation report à nouveau</td><td class="n">${eur(aff.report_a_nouveau)}</td></tr>
      <tr><td>Dividendes bruts</td><td>${sN("saisies.capitaux.dividendes")}</td></tr><tr><td>Au compte de l'exploitant</td><td>${sN("saisies.capitaux.compte_exploitant")}</td></tr>
      <tr><td>Autres (à détailler)</td><td>${sN("saisies.capitaux.autres_1")}</td></tr><tr><td>Autres (à détailler)</td><td>${sN("saisies.capitaux.autres_2")}</td></tr><tr><td>Autres (à détailler)</td><td>${sN("saisies.capitaux.autres_3")}</td></tr>
      <tr class="total"><td>Reste à affecter ${aff.alerte ? `<span class="pastille alerte">${esc(aff.alerte)}</span>` : '<span class="pastille ok">Justifié</span>'}</td><td class="n">${eur(aff.a_detailler, "0,00")}</td></tr></tbody></table></div></div>`;
};

const LIB_TAUX = { "20": "20 %", "10": "10 %", "8,5": "8,5 %", "5,5": "5,5 %", "0": "0 %", "INTRA": "Intracom.", "EXTRA": "Export" };
const CLES_TAUX = ["20", "10", "8,5", "5,5", "0", "INTRA", "EXTRA"];
VUES.ca_tva = (r, d) => {
  const sous = E.sous.ca_tva || "ca";
  const nav = `<div class="sous-onglets">${[["ca", "Cadrage du CA"], ["recap", "Déclarations de TVA"], ["solde", "Cadrage TVA sur le solde"], ["flux", "Cadrage TVA sur les flux"]].map(([k, l]) => `<button data-sous="${k}" class="${k === sous ? "actif" : ""}">${l}</button>`).join("")}</div>`;
  const ca = r.cadrage_ca;
  if (sous === "ca") {
    const lignesSaisie = [["fae_n1", "+ Extourne FAE HT N-1"], ["aae_n1", "− Extourne AAE HT N-1"], ["pca_n1", "− Extourne PCA HT N-1"], ["fae_n", "− FAE HT de l'année"], ["aae_n", "+ AAE HT de l'année"], ["pca_n", "+ PCA HT de l'année"],
      ["cessions", "+ Cessions d'immobilisations HT"], ["debours", "+ Débours HT"]];
    const clients = [["client_411_n1", "411 clients TTC N-1"], ["client_416_n1", "416 clients douteux TTC N-1"], ["client_4191_n1", "4191 acomptes TTC N-1"], ["client_411_n", "411 clients TTC N"], ["client_416_n", "416 clients douteux TTC N"], ["client_4191_n", "4191 acomptes TTC N"], ["pertes", "Pertes irrécouvrables / charges exc."], ["produits_exc", "Produits exceptionnels"]];
    const col = (k, l, f = eur) => `<tr><td>${l}</td>${CLES_TAUX.map(t => `<td class="n">${f(ca.colonnes[t][k])}</td>`).join("")}</tr>`;
    const saisie = (k, l) => `<tr><td>${l}</td>${CLES_TAUX.map(t => `<td>${sN(`saisies.cadrage_ca.colonnes.${t}.${k}`)}</td>`).join("")}</tr>`;
    return nav + `<div class="carte"><h2>Comptes de chiffre d'affaires <span class="aide">Total : ${eur0(ca.total_ca)}</span></h2>
      <table class="t"><thead><tr><th>Compte</th><th>Libellé</th><th class="n">Solde N</th><th class="n">Solde N-1</th><th style="width:130px">Taux de TVA</th><th style="width:150px">Type (liasse)</th></tr></thead><tbody>
      ${ca.comptes.map(c => `<tr><td class="compte">${esc(c.compte)}</td><td class="lib">${esc(c.libelle)}</td><td class="n">${eur(c.n)}</td><td class="n">${eur(c.n1)}</td>
        <td>${sS(`saisies.cadrage_ca.comptes.${c.compte}.taux`, [["", "—"], ...CLES_TAUX.map(t => [t, LIB_TAUX[t]])])}</td><td>${sS(`saisies.cadrage_ca.comptes.${c.compte}.type`, ["", "Marchandises", "Services"])}</td></tr>`).join("") || '<tr><td colspan="6" class="vide">Pas de compte 70.</td></tr>'}</tbody></table></div>
      <div class="carte"><h2>Reconstitution du chiffre d'affaires facturé et encaissé</h2><div class="defile" style="max-height:none"><table class="t"><thead><tr><th></th>${CLES_TAUX.map(t => `<th class="n">${LIB_TAUX[t]}</th>`).join("")}</tr></thead><tbody>
        ${col("ht_realise", "<b>CA HT réalisé sur l'exercice</b>")}<tr class="titre"><td colspan="8">Corrections du début et de la fin d'exercice</td></tr>
        ${lignesSaisie.map(([k, l]) => saisie(k, l)).join("")}
        ${col("ca_facture", "<b>CA facturé sur l'exercice</b>")}${col("tva_ca", "TVA sur CA facturé")}${col("autres", "Autres produits (cessions)")}${col("tva_autres", "TVA sur autres produits")}
        <tr class="total"><td>Facturation TTC de l'année</td>${CLES_TAUX.map(t => `<td class="n">${eur(ca.colonnes[t].facturation_ttc)}</td>`).join("")}</tr>
        <tr class="titre"><td colspan="8">Soldes clients et corrections exceptionnelles (TTC)</td></tr>${clients.map(([k, l]) => saisie(k, l)).join("")}
        ${col("solde_client_n1", "<b>Solde client TTC N-1</b>")}${col("solde_client_n", "<b>Solde client TTC N</b>")}${col("corrections_ttc", "Corrections TTC")}</tbody></table></div>
        <h3>Rapprochement des soldes clients avec la balance</h3><table class="t" style="max-width:720px"><thead><tr><th>Compte</th><th class="n">Balance N-1</th><th class="n">Balance N</th><th class="n">Écart N-1</th><th class="n">Écart N</th></tr></thead><tbody>
        ${ca.controles.map(c => `<tr><td>${esc(c.libelle)}</td><td class="n">${eur(c.n1)}</td><td class="n">${eur(c.n)}</td><td class="n">${eur(c.ecart_n1, "0,00")}</td><td class="n">${eur(c.ecart_n, "0,00")}</td></tr>`).join("")}</tbody></table>
        <p class="note">La ligne « Autres produits » reprend les cessions seules, comme l'Excel (les débours HT n'entrent pas dans la facturation TTC) : point à valider.</p></div>`;
  }
  if (sous === "recap") {
    const rc = r.tva.recap;
    const codes = [["A1", "A1 Ventes, prestations"], ["A2", "A2 Autres opérations imposables"], ["A3", "A3 Achats de services intracom."], ["A4", "A4 Importations"], ["B2", "B2 Acquisitions intracom."], ["E1", "E1 Exportations"], ["E2", "E2 Autres opérations non imposables"], ["F2", ""],
      ["08", "08 Base 20 %"], ["08_taxe", "TVA 20 %"], ["09", "09 Base 5,5 %"], ["09_taxe", "TVA 5,5 %"], ["9B", "9B Base 10 %"], ["9B_taxe", "TVA 10 %"], ["10", "10 Base 8,5 %"], ["10_taxe", "TVA 8,5 %"],
      ["15", "15 TVA antérieurement déduite à reverser"], ["16", "16 Total TVA brute due"], ["17", "17 dont TVA intracom."], ["19", "19 TVA déductible immobilisations"], ["20", "20 TVA déductible autres biens et services"], ["21", "21 Autre TVA à déduire"], ["22", "22 Report de crédit"], ["23", "23 Total TVA déductible"], ["25", "25 Crédit de TVA"], ["27", "27 Crédit à reporter"], ["28", "28 TVA nette due"]].filter(([k, l]) => l);
    return nav + `<div class="carte"><h2>Récapitulatif des déclarations de TVA <span class="aide">${d.mois_tva.length ? `${d.mois_tva.length} mois importés` : "rien d'importé"}</span></h2>
      ${(() => { const src = (d.saisies.tva || {}).source; return src ? `<p><span class="pastille bleu">Source : ${esc(src.origine)}, ${src.declarations} déclaration(s), le ${dateFr(src.le)}</span>${(src.ecartees || []).length ? ` <span class="pastille alerte">${src.ecartees.length} écartée(s) : contrôle non concluant</span>` : ""}</p>` : ""; })()}
      ${rc.mois_manquants.length ? `<p><span class="pastille alerte">Mois sans déclaration : ${esc(rc.mois_manquants.join(", "))}</span></p>` : ""}
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primaire" data-action="import-comptazap">${ic("importer")} Importer depuis ComptaZap</button>
      <button class="btn" data-action="import-tva">Importer l'export Pennylane (fichier)</button></div>
      <div id="cz-bloc" style="margin-top:12px"></div>
      ${rc.colonnes.length ? `<div class="defile" style="margin-top:12px"><table class="t"><thead><tr><th>Ligne</th>${rc.colonnes.map(c => `<th class="n">${esc(c.libelle)}</th>`).join("")}<th class="n">Total</th></tr></thead><tbody>
        ${codes.map(([k, l]) => `<tr class="${["16", "23", "28"].includes(k) ? "sous" : ""}"><td style="white-space:nowrap">${esc(l)}</td>${rc.colonnes.map(c => `<td class="n">${eur(c.valeurs[k])}</td>`).join("")}<td class="n"><b>${eur(rc.totaux[k])}</b></td></tr>`).join("")}
        <tr><td>26 Remboursement demandé</td>${rc.colonnes.map(c => `<td>${sN("saisies.tva.remboursements." + c.mois)}</td>`).join("")}<td class="n">${eur(rc.totaux["26"])}</td></tr></tbody></table></div>` : ""}</div>`;
  }
  if (sous === "solde") {
    const so = r.tva.solde, taxes = ["20", "10", "8,5", "5,5"];
    const lig = (k, l, f = eur) => `<tr><td>${l}</td>${taxes.map(t => `<td class="n">${f(so.colonnes[t][k])}</td>`).join("")}</tr>`;
    const sig = (k, l) => `<tr><td>${l}</td>${taxes.map(t => { const v = so.colonnes[t][k]; return `<td class="n"><span class="pastille ${v === "ok" ? "ok" : "alerte"}">${esc(v)}</span></td>`; }).join("")}</tr>`;
    return nav + `<div class="deux"><div class="carte"><h2>Comptes de TVA collectée (4457)</h2><table class="t"><thead><tr><th>Compte</th><th>Libellé</th><th class="n">Solde N</th><th class="n">Solde N-1</th><th style="width:110px">Taux</th></tr></thead><tbody>
        ${so.comptes.map(c => `<tr><td class="compte">${esc(c.compte)}</td><td class="lib">${esc(c.libelle)}</td><td class="n">${eur(c.n)}</td><td class="n">${eur(c.n1)}</td><td>${sS(`saisies.tva_solde.types.${c.compte}`, [["20", "20 %"], ["10", "10 %"], ["8,5", "8,5 %"], ["5,5", "5,5 %"]], "20")}</td></tr>`).join("") || '<tr><td colspan="5" class="vide">Pas de compte 4457.</td></tr>'}</tbody></table></div>
      <div class="carte"><h2>TVA théorique d'après le solde client</h2><table class="t"><thead><tr><th></th>${taxes.map(t => `<th class="n">${LIB_TAUX[t]}</th>`).join("")}</tr></thead><tbody>
        <tr class="titre"><td colspan="5">Exercice N-1</td></tr>${lig("solde_client_n1", "Solde client TTC")}${lig("tva_theorique_n1", "TVA théorique")}${lig("tva_reelle_n1", "TVA au bilan (4457)")}${lig("ecart_n1", "Écart en TVA")}${sig("signal_n1", "")}${lig("ecart_ht_n1", "Écart en base HT")}
        <tr class="titre"><td colspan="5">Exercice N</td></tr>${lig("solde_client_n", "Solde client TTC")}${lig("tva_theorique_n", "TVA théorique")}${lig("tva_reelle_n", "TVA au bilan (4457)")}${lig("ecart_n", "Écart en TVA")}${sig("signal_n", "")}${lig("ecart_ht_n", "Écart en base HT")}</tbody></table></div></div>`;
  }
  const fl = r.tva.flux;
  const lig = (k, l, f = eur) => `<tr><td>${l}</td>${CLES_TAUX.map(t => `<td class="n">${f(fl.colonnes[t][k])}</td>`).join("")}</tr>`;
  const sig = (k, l) => `<tr><td>${l}</td>${CLES_TAUX.map(t => { const v = fl.colonnes[t][k]; return `<td class="n"><span class="pastille ${v === "ok" ? "ok" : "alerte"}">${esc(v)}</span></td>`; }).join("")}</tr>`;
  return nav + `<div class="carte"><h2>Cadrage de la TVA sur les flux <span class="aide">Base HT encaissée contre base HT déclarée sur l'exercice</span></h2><div class="defile" style="max-height:none"><table class="t"><thead><tr><th></th>${CLES_TAUX.map(t => `<th class="n">${LIB_TAUX[t]}</th>`).join("")}</tr></thead><tbody>
    ${lig("solde_client_n1", "+ Solde client N-1")}${lig("facturation_ttc", "+ Facturation TTC de l'année")}${lig("corrections_ttc", "+/− Corrections exceptionnelles")}${lig("solde_client_n", "− Solde client N")}
    ${lig("encaissements", "<b>Encaissements TTC sur l'année</b>")}${lig("base_theorique", "Base HT théorique à déclarer")}
    <tr><td>Base HT réellement déclarée</td>${CLES_TAUX.map(t => fl.colonnes[t].base_declaree_auto ? `<td class="n">${eur(fl.colonnes[t].base_declaree)}</td>` : `<td>${sN(`saisies.tva_flux.${t}.base_declaree`)}</td>`).join("")}</tr>
    ${lig("ecart", "<b>Écart sur les flux en base HT</b>")}${sig("signal", "")}
    <tr><td>Régularisation de TVA comptabilisée fin N (4458)</td>${CLES_TAUX.map(t => `<td>${sN(`saisies.tva_flux.${t}.regularisation`)}</td>`).join("")}</tr>
    ${lig("ecart_apres_regul", "Écart après régularisation")}${lig("ecart_solde_n", "− Écart sur le solde N (HT)")}${lig("ecart_solde_n1", "− Écart sur le solde N-1 (HT)")}
    <tr class="total"><td>Différence HT à justifier</td>${CLES_TAUX.map(t => `<td class="n">${eur(fl.colonnes[t].difference, "0,00")}</td>`).join("")}</tr>${sig("signal_difference", "")}</tbody></table></div>
    <p class="note">Régularisation : montant positif si elle corrige une insuffisance de déclaration, négatif pour un excédent. Pour 0 %, intracom. et export, elle s'ajoute à la base (l'Excel la neutralisait).</p></div>`;
};

VUES.fiscal = r => {
  const f = r.fiscal, em = r.emprunts, li = r.liasse;
  const sous = E.sous.fiscal || "resultat";
  const nav = `<div class="sous-onglets">${[["resultat", "Résultat fiscal et IS"], ["emprunts", "Emprunts"], ["liasse", "Aide à la liasse"]].map(([k, l]) => `<button data-sous="${k}" class="${k === sous ? "actif" : ""}">${l}</button>`).join("")}</div>`;
  if (sous === "emprunts") {
    return nav + `<div class="carte"><h2>Emprunts (comptes 164) <span class="aide">Capital restant dû et échéancier pour la liasse</span></h2><table class="t"><thead><tr><th>Compte</th><th>Libellé</th><th class="n">CRDU fin ${em.annee - 1}</th><th class="n">CRDU fin ${em.annee}</th><th>CRDU fin ${em.annee + 1}</th><th>CRDU fin ${em.annee + 5}</th><th>Souscrit en ${em.annee}</th></tr></thead><tbody>
      ${em.lignes.map(l => `<tr><td class="compte">${esc(l.compte)}</td><td class="lib">${esc(l.libelle)}</td><td class="n">${eur(l.crdu_n1)}</td><td class="n">${eur(l.crdu_n)}</td><td>${sN(`saisies.emprunts.${l.compte}.crdu_n_plus_1`)}</td><td>${sN(`saisies.emprunts.${l.compte}.crdu_n_plus_5`)}</td><td>${sN(`saisies.emprunts.${l.compte}.souscrit`)}</td></tr>`).join("") || '<tr><td colspan="7" class="vide">Pas d\'emprunt.</td></tr>'}
      <tr class="total"><td colspan="2">Total</td><td class="n">${eur(em.totaux.crdu_n1)}</td><td class="n">${eur(em.totaux.crdu_n)}</td><td class="n">${eur(em.totaux.crdu_n_plus_1)}</td><td class="n">${eur(em.totaux.crdu_n_plus_5)}</td><td class="n">${eur(em.totaux.souscrit)}</td></tr></tbody></table>
      <h3>Pour la liasse</h3><table class="t" style="max-width:640px"><tbody><tr><td>Souscrit en ${em.annee}</td><td class="n">${eur(em.souscrit)}</td></tr><tr><td>Remboursé en ${em.annee}</td><td class="n">${eur(em.rembourse)}</td></tr>
      <tr><td>Montant brut fin ${em.annee}</td><td class="n">${eur(em.montant_brut)}</td></tr><tr><td>À un an au plus</td><td class="n">${eur(em.a_un_an)}</td></tr><tr><td>À plus d'un an et cinq ans au plus</td><td class="n">${eur(em.un_a_cinq_ans)}</td></tr><tr><td>À plus de cinq ans</td><td class="n">${eur(em.plus_de_cinq_ans)}</td></tr></tbody></table></div>`;
  }
  if (sous === "liasse") {
    const chk = (cle, lib, val, guide = "") => `<tr><td>${sC("saisies.liasse.verifie." + cle)}</td><td>${lib}</td><td class="n">${typeof val === "number" ? eur(val, "0,00") : esc(val)}</td><td class="note">${esc(guide)}</td></tr>`;
    return nav + `<div class="carte"><h2>Aide au remplissage de la liasse fiscale <span class="aide">Cochez chaque ligne une fois reportée et vérifiée</span></h2><table class="t"><thead><tr><th style="width:30px">✓</th><th>Élément</th><th class="n">Montant</th><th>Guide (réel 2050 / simplifié 2033)</th></tr></thead><tbody>
      <tr class="titre"><td colspan="4">Chiffre d'affaires (2052 / 2033-B)</td></tr>
      ${chk("ca_mf", "Ventes de marchandises France", li.ca.march_france)}${chk("ca_mi", "Ventes de marchandises intracom. / export", li.ca.march_inter)}${chk("ca_sf", "Prestations France", li.ca.services_france)}${chk("ca_si", "Prestations intracom. / export", li.ca.services_inter)}
      <tr class="${Math.abs(li.ca.ecart) > 0.005 ? "" : "sous"}"><td></td><td>Total ventilé / CA de la balance</td><td class="n">${eur(li.ca.total)} / ${eur(li.ca.balance)}</td><td>${Math.abs(li.ca.ecart) > 0.005 ? `<span class="pastille alerte">Écart ${eur0(li.ca.ecart)} : taux ou type manquant dans le cadrage du CA</span>` : '<span class="pastille ok">OK</span>'}</td></tr>
      <tr class="titre"><td colspan="4">Exceptionnel (2053 / 2033-B)</td></tr>${chk("ch_exc", "Charges exceptionnelles", li.charges_exc)}${chk("pr_exc", "Produits exceptionnels", li.produits_exc)}
      <tr class="titre"><td colspan="4">Emprunts (2057 / plaquette)</td></tr>${chk("emp_s", "Souscrit en cours d'exercice", li.emprunts.souscrit)}${chk("emp_r", "Remboursé en cours d'exercice", li.emprunts.rembourse)}${chk("emp_b", "Montant brut", li.emprunts.montant_brut)}${chk("emp_1", "À un an au plus", li.emprunts.a_un_an)}${chk("emp_5", "À plus d'un an et cinq ans au plus", li.emprunts.un_a_cinq_ans)}${chk("emp_p", "À plus de cinq ans", li.emprunts.plus_de_cinq_ans)}
      <tr class="titre"><td colspan="4">Résultat fiscal (2058-A / 2033-B)</td></tr>${chk("rf_c", esc(li.resultat.libelle), li.resultat.comptable)}${chk("rf_r", "Réintégrations", li.resultat.reintegrations)}${chk("rf_d", "Déductions", li.resultat.deductions)}${chk("rf_i", "Déficit imputé", li.resultat.deficit_impute)}${chk("rf_t", "Résultat fiscal", li.resultat.fiscal)}
      ${chk("def", "Déficit reportable (2058-B / 2033-D)", li.deficit_reportable)}
      <tr class="titre"><td colspan="4">2058-C / 2033-D</td></tr>${chk("div", "Dividendes distribués", li.dividendes_distribues)}${chk("prel", "Prélèvements sur réserves", li.prelevements_reserves)}${chk("tva", "TVA collectée sur l'exercice (théorique)", li.tva_collectee)}
      <tr class="titre"><td colspan="4">CVAE</td></tr><tr><td></td><td>Mono-établissement ${sC("saisies.liasse.mono_etablissement")}</td><td></td><td>${esc(li.cvae.message_1330)}</td></tr>${chk("cvae", "Chiffre d'affaires (1329)", li.cvae.ca, li.cvae.message_1329)}
      <tr class="titre"><td colspan="4">2067 (frais généraux)</td></tr>${chk("r2067", "Rémunérations (644)", li.frais_2067.remunerations, "Vérifier si la 2067 est nécessaire")}${chk("d2067", "Déplacements (6251)", li.frais_2067.deplacements, li.frais_2067.message_deplacements)}${chk("re2067", "Réceptions (6257)", li.frais_2067.restaurants, li.frais_2067.message_restaurants)}${chk("c2067", "Cadeaux (6234)", li.frais_2067.cadeaux, li.frais_2067.message_cadeaux)}
      <tr class="titre"><td colspan="4">2065 et EDI</td></tr><tr><td></td><td>SIREN du cabinet (examen de conformité fiscale)</td><td>${sT("saisies.liasse.siren_cabinet")}</td><td></td></tr>
      ${chk("edi_a", "Résultat net avant IS", li.edi.resultat_avant_is, "Contrôler avant envoi")}${chk("edi_f", "Résultat fiscal", li.edi.resultat_fiscal, "Contrôler avant envoi")}${chk("edi_is", "IS de l'exercice", li.edi.is, "Contrôler avant envoi")}${chk("edi_r", "Résultat net comptable", li.edi.resultat_net, "Contrôler avant envoi")}
      </tbody></table></div>`;
  }
  const reint = [["is", "Impôt sur les sociétés N (695)", "is_force"], ["amendes", "Amendes et pénalités (6582)", "amendes_force"], ["dons", "Dons (6238)", "dons_force"]];
  const autresR = [["tvs", "Taxe sur les véhicules de sociétés"], ["loyers_cb", "Loyers non déductibles crédit-bail"], ["taxe_bureaux_payee", "Taxe sur les bureaux payée"], ["abandon", "Abandon de créance non déductible consenti"], ["sci_ir", "Résultat SCI à l'IR"], ["amort_lmnp", "Amortissements LMNP"], ["divers_reint", "Divers à détailler"]];
  const ded = [["taxe_bureaux_facturee", "Taxe sur les bureaux facturée"], ["subventions_exo", "Subventions exonérées"], ["rmf", "Retour à meilleure fortune non imposable"], ["ci_famille", "Crédit d'impôt famille"], ["cir", "Crédit d'impôt recherche"], ["divers_ded_1", "Divers à détailler"], ["divers_ded_2", "Divers à détailler"], ["divers_ded_3", "Divers à détailler"]];
  return nav + `<div class="deux"><div class="carte"><h2>Résultat fiscal</h2><table class="t"><tbody>
      <tr class="sous"><td>Bénéfice comptable N</td><td class="n">${eur(f.benefice)}</td><td></td></tr>
      <tr class="titre"><td colspan="3">Réintégrations</td></tr>
      ${reint.map(([k, l, force]) => `<tr><td>${l}</td><td class="n">${eur(f.reintegrations[k])}</td><td style="width:130px">${sN("saisies.fiscal." + force, { ph: "forcer…" })}</td></tr>`).join("")}
      ${autresR.map(([k, l]) => `<tr><td>${l}</td><td class="n"></td><td>${sN("saisies.fiscal." + k)}</td></tr>`).join("")}
      <tr class="total"><td>Total des réintégrations</td><td class="n">${eur(f.total_reintegrations)}</td><td></td></tr>
      <tr class="sous"><td>Déficit comptable N</td><td class="n">${eur(f.deficit)}</td><td></td></tr>
      <tr class="titre"><td colspan="3">Déductions</td></tr>
      <tr><td>Dividendes reçus (régime mère-fille), QP de frais et charges de ${pct(f.taux_qp_smf)}</td><td class="n">${eur(f.deductions.smf)}</td><td>${sN("saisies.fiscal.dividende_smf", { ph: "dividende" })}</td></tr>
      <tr><td>Taux de la quote-part de frais et charges</td><td></td><td>${sN("saisies.fiscal.taux_qp_smf", { ph: "0,05" })}</td></tr>
      ${ded.map(([k, l]) => `<tr><td>${l}</td><td class="n"></td><td>${sN("saisies.fiscal." + k)}</td></tr>`).join("")}
      <tr class="total"><td>Total des déductions</td><td class="n">${eur(f.total_deductions)}</td><td></td></tr>
      <tr class="sous"><td>Résultat fiscal avant imputation des déficits</td><td class="n">${eur(f.avant_imputation, "0,00")}</td><td></td></tr>
      <tr><td>Déficit antérieur reportable (liasse N-1)</td><td></td><td>${sN("saisies.fiscal.deficit_anterieur")}</td></tr>
      <tr><td>Plafond d'imputation (1 M€ + 50 % au-delà, dans la limite du bénéfice)</td><td class="n">${eur(f.plafond_imputation)}</td><td></td></tr>
      <tr><td>Déficit imputé sur N</td><td class="n">${eur(f.deficit_impute)}</td><td></td></tr><tr><td>Déficit restant à reporter</td><td class="n">${eur(f.deficit_restant)}</td><td></td></tr>
      <tr class="total"><td>Résultat fiscal après imputation des déficits</td><td class="n">${eur(f.apres_imputation, "0,00")}</td><td></td></tr></tbody></table></div>
    <div class="carte"><h2>${esc(f.intitule)}</h2><div class="grille-form"><div><label>Soumise à l'IS ?</label>${sS("saisies.fiscal.soumise_is", ["OUI", "NON"], "OUI")}</div><div><label>Taux réduit de 15 % ?</label>${sS("saisies.fiscal.taux_reduit", ["Oui", "Non"], "Oui")}</div></div>
      <table class="t" style="margin-top:12px"><tbody><tr><td>Plafond du taux réduit${r.infos.debut_activite ? " (prorata 1er exercice)" : ""}</td><td class="n">${eur(f.plafond_taux_reduit)}</td></tr>
      <tr><td>IS à ${pct(f.taux_reduit)}</td><td class="n">${eur(f.is_taux_reduit)}</td></tr><tr><td>Base au taux normal</td><td class="n">${eur(f.base_taux_normal)}</td></tr>
      <tr><td>IS à ${pct(f.taux_normal)}</td><td class="n">${eur(f.is_taux_normal)}</td></tr><tr class="total"><td>Total IS</td><td class="n">${eur(f.is_total, "0,00")}</td></tr>
      <tr><td>IS comptabilisé (695)</td><td class="n">${eur(f.reintegrations.is, "0,00")}</td></tr>
      <tr class="sous"><td>Résultat net comptable ajusté</td><td class="n">${eur(f.resultat_net_ajuste)}</td></tr></tbody></table>
      ${Math.abs(f.reintegrations.is - f.is_total) > 1 ? `<div class="note-correction">L'IS calculé (${eur0(f.is_total)}) diffère de l'IS comptabilisé (${eur0(f.reintegrations.is)}) : écriture d'IS à ajuster.</div>` : ""}
      <p class="note">Déficits : l'imputation est plafonnée au bénéfice de l'exercice. L'Excel pouvait imputer plus que le bénéfice et faire disparaître le déficit restant.</p></div></div>`;
};

VUES.tns = r => {
  const p = r.tns.provision, dr = r.tns.driti, pa = r.tns.pamc, ec = r.tns.ecritures, dm = r.tns.driti_manuelle;
  const sous = E.sous.tns || "provision";
  const nav = `<div class="sous-onglets">${[["provision", "Provision des cotisations"], ["driti", "DRITI et 2042"], ["pamc", "PAMC"], ["manuelle", "DRITI manuelle"]].map(([k, l]) => `<button data-sous="${k}" class="${k === sous ? "actif" : ""}">${l}</button>`).join("")}</div>`;
  const cases = (o, pre) => `<table class="t"><tbody><tr class="titre"><td colspan="2">2042 : traitements et salaires</td></tr><tr><td><b>1GB</b> Revenus des gérants (art. 62)</td><td class="n">${eur(o["1GB"])}</td></tr>
    <tr class="titre"><td colspan="2">DRITI</td></tr><tr><td><b>DSCA</b> Cotisations sociales obligatoires à réintégrer</td><td class="n">${eur(o.DSCA)}</td></tr><tr><td><b>DSDA</b> Cotisations obligatoires à déduire</td><td class="n">${eur(o.DSDA)}</td></tr>
    <tr><td><b>DSEA</b> Cotisations facultatives</td><td class="n">${eur(o.DSEA)}</td></tr><tr><td><b>DSAA</b> Dividendes (société IS)</td><td class="n">${eur(o.DSAA)}</td></tr></tbody></table>`;
  if (sous === "driti") return nav + `<div class="deux"><div class="carte"><h2>Cases à reporter <span class="aide">${esc(p.nom)} · ${p.annee}</span></h2>${cases(dr)}</div>
    <div class="carte"><h2>Détail</h2><table class="t"><tbody>${[["remuneration", "Rémunération nette"], ["avantages_nature", "Avantages en nature"], ["madelins_excedent", "Madelin au-delà du plafond"], ["csg_non_deductible", "CSG/CRDS non déductible"], ["cotisations_payees", "Cotisations réglées sur l'année"], ["csg_appelee", "CSG/CRDS appelée"], ["cotisations_remboursees", "Cotisations remboursées"], ["per_deductible", "PER déductible"], ["prevoyance_deductible", "Prévoyance et mutuelle déductibles"], ["dividendes_cotis", "Dividendes soumis à cotisations"]].map(([k, l]) => `<tr><td>${l}</td><td class="n">${eur(dr[k])}</td></tr>`).join("")}</tbody></table></div></div>`;
  if (sous === "pamc") return nav + `<div class="carte"><h2>Praticiens et auxiliaires médicaux conventionnés</h2><div class="grille-form" style="max-width:640px"><div><label>CA total (conventionné et non conventionné)</label>${sN("saisies.pamc.ca_total")}</div><div><label>Honoraires pour actes (SNIR)</label>${sN("saisies.pamc.honoraires_snir")}</div></div>
    <table class="t" style="margin-top:12px;max-width:720px"><tbody><tr><td>Quote-part conventionnée</td><td class="n">${pct(pa.quote_part)}</td></tr><tr><td>Revenus nets totaux</td><td class="n">${eur(pa.revenus_nets)}</td></tr>
    <tr><td><b>DSCS</b> Recettes des activités non salariées</td><td class="n">${eur(pa.DSCS)}</td></tr><tr><td><b>DSGA</b> Revenu net de l'activité conventionnée</td><td class="n">${eur(pa.DSGA)}</td></tr><tr><td><b>DSCR</b> Revenu net des autres activités</td><td class="n">${eur(pa.DSCR)}</td></tr>
    <tr><td><b>DSAR</b> Cotisations facultatives (conventionné)</td><td class="n">${eur(pa.DSAR)}</td></tr><tr><td><b>DSCM</b> Cotisations facultatives (autres)</td><td class="n">${eur(pa.DSCM)}</td></tr></tbody></table>
    <p class="note"><a href="https://mon-entreprise.urssaf.fr/assistants/declaration-revenus-pam" target="_blank" rel="noopener">Assistant URSSAF de déclaration des revenus PAM</a></p></div>`;
  if (sous === "manuelle") return nav + `<div class="deux"><div class="carte"><h2>Saisie manuelle</h2><table class="t"><tbody>${[["remuneration", "Rémunération nette"], ["avantages_nature", "Avantages en nature"], ["madelins_excedent", "Madelin au-delà du plafond"], ["csg_non_deductible", "CSG/CRDS non déductible appelée"], ["cotisations_payees", "Cotisations et contributions réglées"], ["csg_appelee", "CSG/CRDS appelée"], ["cotisations_remboursees", "Cotisations remboursées"], ["per_deductible", "PER réglé"], ["prevoyance_deductible", "Mutuelle et prévoyance réglées"], ["dividendes_cotis", "Dividendes soumis à cotisations"]].map(([k, l]) => `<tr><td>${l}</td><td style="width:150px">${sN("saisies.driti_manuelle." + k)}</td></tr>`).join("")}</tbody></table></div>
    <div class="carte"><h2>Cases à reporter</h2>${cases(dm)}</div></div>`;
  const champs = [["per", "Cotisations PER de l'année civile"], ["plafond_retraite", "Plafond retraite (simulateur)"], ["prevoyance", "Prévoyance + mutuelle de l'année civile"], ["plafond_prevoyance", "Plafond prévoyance + mutuelle (simulateur)"],
    ["dividendes_cotis", "Dividendes soumis aux cotisations (2CG)"], ["csg_non_deductible", "CSG/CRDS non déductible (attestation)"], ["csg_deductible", "CSG/CRDS déductible (attestation)"], ["cotisations_payees", "Cotisations payées sur l'année (banque)"],
    ["cotisations_remboursees", "Cotisations remboursées sur l'année"], ["avantages_nature", "Avantages en nature"], ["remuneration", "Rémunération nette du gérant"], ["cotisations_urssaf", "Cotisations calculées sur le site de l'URSSAF"]];
  return nav + `<div class="deux"><div class="carte"><h2>Gérant majoritaire TNS : éléments</h2><div class="grille-form"><div><label>Nom du gérant</label>${sT("saisies.tns.nom")}</div><div><label>Mois de clôture</label>${sN("saisies.tns.mois_cloture", { ph: String(p.mois_cloture) })}</div><div><label>PASS ${p.annee}</label>${sN("saisies.tns.pass", { ph: NF0.format(p.pass) })}</div></div>
      <table class="t" style="margin-top:12px"><tbody>${champs.map(([k, l]) => `<tr><td>${l}</td><td style="width:150px">${sN("saisies.tns." + k)}</td></tr>`).join("")}</tbody></table>
      <p class="note"><a href="https://www.urssaf.fr/accueil/outils-documentation/simulateurs/revenus-independant.html" target="_blank" rel="noopener">Simulateur URSSAF des revenus d'indépendant</a> : rémunération à saisir ${eur0(p.remuneration_simulateur)}.</p></div>
    <div class="carte"><h2>Calculs</h2><table class="t"><tbody>
      <tr><td>Madelin retraite au-delà du plafond (à réintégrer, 1GB)</td><td class="n">${eur(p.excedent_per)}</td></tr><tr><td>Madelin prévoyance au-delà du plafond</td><td class="n">${eur(p.excedent_prevoyance)}</td></tr>
      <tr class="sous"><td>Revenu fiscal à déclarer (1GB)</td><td class="n">${eur(p.revenu_fiscal)}</td></tr><tr><td>Base sociale « super brut »</td><td class="n">${eur(p.base_super_brut)}</td></tr>
      <tr><td>Abattement 26 % (plancher ${eur0(p.plancher)}, plafond ${eur0(p.plafond)})</td><td class="n">${eur(p.abattement)}</td></tr><tr class="sous"><td>Base sociale (CSG-CRDS)</td><td class="n">${eur(p.base_sociale)}</td></tr>
      <tr class="titre"><td colspan="2">Cotisations à provisionner</td></tr><tr><td>Cotisations (URSSAF)</td><td class="n">${eur(p.cotisations_urssaf)}</td></tr><tr><td>Contribution à la formation professionnelle</td><td class="n">${eur(p.cfp)}</td></tr>
      <tr><td>CSG/CRDS 9,7 %</td><td class="n">${eur(p.csg_crds)}</td></tr><tr><td>dont déductible 6,8 %</td><td class="n">${eur(p.csg_deductible_calc)}</td></tr><tr class="total"><td>Cotisations totales</td><td class="n">${eur(p.cotisations_totales)}</td></tr>
      <tr><td>Taux rapporté au revenu social</td><td class="n">${pct(p.taux_revenu_social)}</td></tr><tr><td>Taux rapporté au revenu net</td><td class="n">${pct(p.taux_revenu_net)}</td></tr></tbody></table>
      <h3>Écritures de provision</h3><table class="t"><thead><tr><th>Date</th><th>Compte</th><th>Libellé</th><th class="n">Débit</th><th class="n">Crédit</th></tr></thead><tbody>
      ${ec.lignes.map(l => `<tr><td>${dateFr(l.date)}</td><td>${esc(l.compte)}</td><td>${esc(l.libelle)}</td><td class="n">${eur(l.debit)}</td><td class="n">${eur(l.credit)}</td></tr>`).join("")}
      <tr class="total"><td colspan="3">Total</td><td class="n">${eur(ec.total_debit)}</td><td class="n">${eur(ec.total_credit)}</td></tr></tbody></table><p class="note">Sous réserve que les comptes 646 et 641 soient soldés avant l'écriture.</p></div></div>`;
};

VUES.ir = r => {
  const el = r.ir.elements, rc = r.ir.recap;
  const noms1 = r.ago_n1.associes.map(a => a.nom), noms = r.ago_n.repartition.associes.map(a => a.nom);
  const ifu = (o, chemin, noms_, titre) => `<div class="carte"><h2>${titre}</h2><div class="grille-form" style="max-width:320px"><div><label>Associé</label>${sS(chemin, ["", ...noms_])}</div></div>
    ${o.trouve ? `<table class="t" style="margin-top:10px"><tbody><tr><td><b>2DC</b> Revenus des actions et parts</td><td class="n">${eur(o["2DC"])}</td></tr><tr><td><b>2CG</b> Revenus déjà soumis aux PS sans CSG déductible</td><td class="n">${eur(o["2CG"])}</td></tr>
    <tr><td><b>2BH</b> Revenus déjà soumis aux PS avec CSG déductible</td><td class="n">${eur(o["2BH"])}</td></tr><tr><td><b>2CK</b> Prélèvement forfaitaire non libératoire versé</td><td class="n">${eur(o["2CK"])}</td></tr></tbody></table>` : '<p class="note">Choisissez l\'associé.</p>'}</div>`;
  return `<div class="deux"><div class="carte"><h2>Situation du dirigeant <span class="aide">Revenus ${r.ir.annee}</span></h2><table class="t"><thead><tr><th>Élément</th><th>Concerné</th><th class="n">Valeur</th></tr></thead><tbody>
      <tr><td>Indemnité d'occupation (revenus fonciers)</td><td>${sS("infos.concerne_indemnite_rf", ["NON", "OUI"], "NON")}</td><td>${sN("infos.indemnite_rf")}</td></tr>
      <tr><td>Indemnité d'occupation (micro-LMNP)</td><td>${sS("infos.concerne_indemnite_micro", ["NON", "OUI"], "NON")}</td><td>${sN("infos.indemnite_micro")}</td></tr>
      <tr><td>Revenu BIC (résultat fiscal)</td><td>${sS("infos.concerne_bic", ["NON", "OUI"], "NON")}</td><td class="n">${eur(el.bic.valeur)}</td></tr>
      <tr><td>Revenu LMP (résultat fiscal)</td><td>${sS("infos.concerne_lmp", ["NON", "OUI"], "NON")}</td><td class="n">${eur(el.lmp.valeur)}</td></tr>
      <tr><td>Revenu LMNP (résultat fiscal)</td><td>${sS("infos.concerne_lmnp", ["NON", "OUI"], "NON")}</td><td class="n">${eur(el.lmnp.valeur)}</td></tr></tbody></table></div>
    <div class="carte"><h2>Cases de la déclaration 2042 / 2042-C-PRO</h2><table class="t"><tbody>
      ${rc.sections.indemnite_rf ? `<tr class="titre"><td colspan="2">Revenus fonciers</td></tr><tr><td><b>4BE</b> Recettes brutes (micro-foncier)</td><td class="n">${eur(rc["4BE"])}</td></tr>` : ""}
      ${rc.sections.indemnite_micro ? `<tr class="titre"><td colspan="2">Locations meublées non professionnelles (micro)</td></tr><tr><td><b>5ND</b> Locations meublées, cas général</td><td class="n">${eur(rc["5ND"])}</td></tr>` : ""}
      ${rc.sections.bic ? `<tr class="titre"><td colspan="2">BIC professionnels (y compris LMP)</td></tr><tr><td><b>5KC</b> Revenus imposables</td><td class="n">${eur(rc["5KC"])}</td></tr><tr><td><b>5KF</b> Déficits</td><td class="n">${eur(rc["5KF"])}</td></tr>
        <tr class="titre"><td colspan="2">BIC non professionnels</td></tr><tr><td><b>5NC</b> Revenus imposables</td><td class="n">${eur(rc["5NC"])}</td></tr><tr><td><b>5NF</b> Déficits</td><td class="n">${eur(rc["5NF"])}</td></tr><tr><td><b>5HY</b> À soumettre aux prélèvements sociaux</td><td class="n">${eur(rc["5HY"])}</td></tr>` : ""}
      ${rc.sections.lmnp ? `<tr class="titre"><td colspan="2">LMNP au réel</td></tr><tr><td><b>5NA</b> Revenus imposables</td><td class="n">${eur(rc["5NA"])}</td></tr><tr><td><b>5NY</b> Déficits</td><td class="n">${eur(rc["5NY"])}</td></tr>` : ""}
      ${!Object.values(rc.sections).some(Boolean) ? '<tr><td class="vide" colspan="2">Cochez « OUI » sur les éléments concernés.</td></tr>' : ""}</tbody></table></div></div>
    <div class="deux">${ifu(r.ir.ifu_n1, "saisies.ifu.associe_n1", noms1, `Dividendes perçus en ${r.ir.annee} (AG N-1)`)}${ifu(r.ir.ifu_n, "saisies.ifu.associe_n", noms, `Dividendes à percevoir en ${r.ir.annee + 1} (AG sur N)`)}</div>`;
};

VUES.social = (r, d) => {
  const so = r.social;
  return `<div class="carte"><h2>Cadrage social (journal de paie SILAE) <span class="aide">${d.nb_paie ? d.nb_paie + " lignes importées" : "rien d'importé"}</span></h2>
    <p>Importez le journal de paie annuel (colonnes Code, Libellé, Salarial, Patronal) ou collez-le depuis Excel.</p><button class="btn" data-action="import-paie">${ic("importer")} Importer le journal de paie</button>
    ${so.codes_a_parametrer.length ? `<div class="note-correction">Codes de rubrique sans organisme : ${esc(so.codes_a_parametrer.join(", "))}. Leurs cotisations patronales ne sont pas ventilées.</div>` : ""}
    <table class="t" style="margin-top:12px"><thead><tr><th>Élément</th><th class="n">Paie</th><th style="width:150px">Comptabilité</th><th class="n">Écart</th><th>Commentaire</th></tr></thead><tbody>
    ${so.rapprochement.map(x => `<tr><td>${esc(x.element)}</td><td class="n">${x.element === "Provision CP (à la main)" ? sN("saisies.social.provision_cp") : x.paie === null ? '<span class="pastille alerte">Brut non trouvé</span>' : eur(x.paie)}</td>
      <td>${x.element === "Provision CP (à la main)" ? "" : sN("saisies.social.compta." + x.element)}</td><td class="n">${x.element === "Provision CP (à la main)" ? "" : eur(x.ecart, "0,00")}</td><td>${sT("saisies.social.commentaires." + x.element)}</td></tr>`).join("")}</tbody></table></div>
    ${so.lignes.length ? `<div class="carte"><h2>Journal importé</h2><div class="defile"><table class="t"><thead><tr><th>Code</th><th>Libellé</th><th class="n">Salarial</th><th class="n">Patronal</th><th>Organisme</th></tr></thead><tbody>
      ${so.lignes.map(l => `<tr><td>${esc(l.code)}</td><td>${esc(l.libelle)}</td><td class="n">${eur(l.salarial)}</td><td class="n">${eur(l.patronal)}</td><td class="note">${esc(l.organisme)}</td></tr>`).join("")}</tbody></table></div></div>` : ""}`;
};

VUES.questionnaires = r => {
  const sous = E.sous.questionnaires || "lab";
  const q = r.questionnaires[sous], def = q.definition;
  const nav = `<div class="sous-onglets">${[["lab", "Acceptation / maintien"], ["revision", "Révision"], ["bouclage", "Bouclage"]].map(([k, l]) => { const a = r.questionnaires[k].avancement; return `<button data-sous="${k}" class="${k === sous ? "actif" : ""}">${l}<small>${a.fait}/${a.total}</small></button>`; }).join("")}</div>`;
  const base = "saisies.quest_" + sous;
  let h = `<div class="carte"><h2>${esc(def.titre)}</h2>`;
  def.sections.forEach((sec, i) => {
    const titre = sec[0], questions = sec[sec.length - 1], type = sec.length === 3 ? sec[1] : null;
    h += `<h3>${esc(titre)}</h3>`;
    questions.forEach((txt, j) => {
      const c = `${base}.${i}.${j}`;
      if (sous === "lab") h += `<div class="question large"><div>${esc(txt)}</div><div>${sS(c + ".reponse", type === "risque" ? def.reponses_risque : def.reponses)}</div><div>${sT(c + ".note", { ph: "Observation" })}</div></div>`;
      else h += `<div class="question large"><div>${esc(txt)}</div><div>${sS(c + ".statut", def.reponses, "A faire")}</div><div style="display:flex;gap:8px;align-items:center">${sC(c + ".fait")}<span class="note">Fait</span>${sT(c + ".note", { ph: "Observation" })}</div></div>`;
    });
  });
  if (sous === "lab") h += `<h3>Décision</h3><p>${esc(def.attestation)}</p>${sS(base + ".decision", ["", ...def.decisions])}<div class="grille-form" style="margin-top:10px"><div><label>Expert-comptable signataire</label>${sT(base + ".signataire")}</div><div><label>Date</label>${sT(base + ".date", { type: "date" })}</div></div>`;
  return nav + h + `<h3>Observations générales</h3>${sZ(base + ".observations")}</div>`;
};

VUES.mail = (r, d) => {
  const m = r.mail;
  const ligneVal = l => l.pourcentage ? pct(l.n) : eur0(l.n);
  const corps = texteMail(r, d);
  return `<div class="deux"><div class="carte"><h2>Chiffres clés au ${esc(m.date_n)}</h2><table class="t"><thead><tr><th>Élément</th><th class="n">${esc(m.date_n)}</th><th class="n">${esc(m.date_n1)}</th><th class="n">Variation</th><th class="n">%</th></tr></thead><tbody>
      ${m.groupes.map(g => `<tr class="titre"><td colspan="5">${esc(g.titre)}</td></tr>` + g.lignes.map(l => `<tr class="${l.pourcentage ? "detail" : ""}"><td>${esc(l.libelle)}</td><td class="n">${l.pourcentage ? pct(l.n) : eur(l.n)}</td><td class="n">${l.pourcentage ? pct(l.n1) : eur(l.n1)}</td><td class="n">${"var" in l ? eur(l.var) : ""}</td><td class="n">${"var_pct" in l ? pct(l.var_pct) : ""}</td></tr>`).join("")).join("")}</tbody></table></div>
    <div><div class="carte"><h2>Échéances à prévoir</h2><table class="t"><tbody>${m.echeances.map((e, i) => `<tr><td>${sC("saisies.mail." + ["inclure_is", "inclure_tva", "inclure_flat_tax"][i], true)} ${esc(e.libelle)}</td><td class="n">${eur(e.montant)}</td><td>${esc(e.echeance)}</td></tr>`).join("")}</tbody></table>
      ${m.dividendes.length ? `<h3>Dividendes à verser</h3><table class="t"><thead><tr><th>Associé</th><th class="n">Brut</th><th class="n">Précompte IR</th><th class="n">PS</th><th class="n">Virement</th><th>Date</th></tr></thead><tbody>${m.dividendes.map(x => `<tr><td>${esc(x.associe)}</td><td class="n">${eur(x.brut)}</td><td class="n">${eur(x.precompte_ir)}</td><td class="n">${eur(x.precompte_ps)}</td><td class="n">${eur(x.virement)}</td><td>${esc(x.date)}</td></tr>`).join("")}</tbody></table>` : ""}</div>
    <div class="carte"><h2>Projet de mail <span class="aide"><button class="btn petit" data-action="copier-mail">${ic("copier")} Copier</button></span></h2><div class="mail-apercu" id="mail-texte">${esc(corps)}</div></div></div></div>`;
};
function texteMail(r, d) {
  const m = r.mail, v = k => { for (const g of m.groupes) for (const l of g.lignes) if (l.cle === k) return l; return { n: 0, n1: 0 }; };
  const e = x => NF0.format(Math.round(x)) + " €", p = x => PF.format(x || 0);
  const ca = v("ca"), res = v("resultat"), ebe = v("ebe"), tre = v("tresorerie"), cp = v("capitaux_propres");
  let t = `Bonjour,\n\nVoici les chiffres clés de l'exercice clos le ${m.date_n} :\n\n`;
  t += `• Chiffre d'affaires : ${e(ca.n)} (${e(ca.n1)} en N-1, ${ca.n1 ? (ca.n >= ca.n1 ? "+" : "") + p(ca.var_pct) : "nouveau"})\n`;
  t += `• EBITDA : ${e(ebe.n)}, soit ${p(v("ebe_pct").n)} du CA\n• Résultat de l'exercice : ${e(res.n)} (${e(res.n1)} en N-1)\n`;
  t += `• Trésorerie : ${e(tre.n)}\n• Capitaux propres : ${e(cp.n)}\n`;
  const ech = m.echeances.filter(x => x.montant);
  if (ech.length) { t += `\nÉchéances à prévoir :\n`; ech.forEach(x => t += `• ${x.libelle} : ${e(Math.abs(x.montant))}${x.echeance ? " au " + x.echeance : ""}\n`); }
  if (m.dividendes.length) { t += `\nDividendes :\n`; m.dividendes.forEach(x => t += `• ${x.associe} : brut ${e(x.brut)}, virement net ${e(x.virement)}${x.date ? " le " + x.date : ""}\n`); }
  return t + `\nNous restons à votre disposition pour en parler.\n\nBien cordialement,\n${E.moi ? E.moi.nom : ""}\n${r.infos.cabinet || ""}`;
}

VUES.infos = (r, d) => {
  const m = d.dossier;
  return `<div class="deux"><div class="carte"><h2>Informations du dossier</h2><div class="grille-form">
      <div><label>Nom du client</label>${sT("dossier.nom")}</div><div><label>SIREN</label>${sT("dossier.siren")}</div>
      <div><label>Forme juridique</label>${sT("infos.forme")}</div><div><label>Cabinet</label>${sT("infos.cabinet")}</div>
      <div><label>Début d'exercice</label>${sT("dossier.debut_exercice", { type: "date" })}</div><div><label>Clôture</label>${sT("dossier.cloture", { type: "date" })}</div>
      <div><label>Début d'activité (1er exercice seulement)</label>${sT("infos.debut_activite", { type: "date" })}</div><div><label>Année fiscale (IR)</label>${sN("infos.annee_ir")}</div></div>
      <h3>Paramètres de calcul</h3><div class="grille-form"><div><label>Cotisations TNS sur dividendes (taux)</label>${sN("parametres.taux_cotis_tns_dividendes", { ph: "0,25" })}</div></div>
      <p class="note">Pennylane : ${m.pennylane_id ? `dossier n° ${esc(m.pennylane_id)}` : "non relié"}${m.jeton_dossier ? " (jeton propre au dossier)" : ""}.</p></div>
    <div class="carte"><h2>Historique <span class="aide"><button class="btn petit" data-action="historique">Afficher</button></span></h2><div id="historique" class="note">Qui a fait quoi, et quand.</div>
      <h3>Zone sensible</h3><button class="btn danger" data-action="supprimer">Supprimer ce dossier</button></div></div>`;
};

// Déclarations de TVA reçues de ComptaZap pour ce dossier (SIREN + exercice)
async function chargerComptazap() {
  const bloc = $("#cz-bloc"); if (!bloc) return;
  if (E.moi.demo) { bloc.innerHTML = `<div class="note-correction">Mode démo : l'import des déclarations déposées (connecteur ComptaZap) est désactivé. Les déclarations affichées ci-dessous sont fictives.</div>`; return; }
  const id = E.dossier.dossier.id;
  let r;
  try { r = await api("GET", `/api/dossiers/${id}/comptazap`); } catch (e) { bloc.innerHTML = `<div class="message-erreur">${esc(e.message)}</div>`; return; }
  if (!$("#cz-bloc") || E.dossier.dossier.id !== id) return;
  const cz = r.connecteur;
  let h = "";
  if (!r.siren) h = `<div class="note-correction">Renseignez le SIREN du dossier (onglet Dossier) : c'est lui qui relie le dossier aux déclarations de ComptaZap.</div>`;
  else if (!cz.lie) h = `<div class="note-correction">Aucun poste relié : installez le connecteur sur le PC de ComptaZap (Paramètres › Connecteur du poste).</div>`;
  else if (!r.declarations.length) h = `<div class="note-correction">Aucune déclaration ComptaZap pour le SIREN ${esc(r.siren)} sur cet exercice. Dernière synchro du poste : ${cz.derniere_synchro ? dateFr(cz.derniere_synchro) + " " + esc(cz.derniere_synchro.slice(11, 16)) : "jamais"}.</div>`;
  else h = `<table class="t"><thead><tr><th>Période</th><th>Formulaire</th><th>Dépôt</th><th class="n">Montant</th><th>Contrôle</th><th></th></tr></thead><tbody>${r.declarations.map(x => `<tr class="${x.retenue ? "" : "detail"}">
      <td>${dateFr(x.periode_debut)} → ${dateFr(x.periode_fin)}</td><td>${esc(x.formulaire)} · ${esc(x.type_depot)}${x.retenue ? "" : " (remplacée)"}</td><td>${esc(x.date_depot)}</td>
      <td class="n">${eur(x.is_credit ? -x.montant : x.montant, "0,00")}${x.is_credit ? " (crédit)" : ""}</td>
      <td>${x.controle_ok ? '<span class="pastille ok">Lue et contrôlée</span>' : `<span class="pastille erreur">À vérifier</span> <span class="note">${esc(x.controle_msg)}</span>`}</td>
      <td>${x.pdf ? `<a href="/api/comptazap/pdf/${esc(x.pdf_sha)}" target="_blank" rel="noopener">PDF</a>` : ""}</td></tr>`).join("")}</tbody></table>
      <p class="note">Une déclaration rectificative remplace l'initiale de la même période. Le montant lu sur le PDF (case 28, ou 25 pour un crédit ; solde après acomptes pour la CA12) est comparé à celui de ComptaZap.</p>`;
  $("#cz-bloc").innerHTML = h;
}

// ---------------------------------------------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------------------------------------------
const ACTIONS = {
  import: () => fenetreImport(),
  "import-comptazap": async () => {
    try { recevoir(await api("POST", `/api/dossiers/${E.dossier.dossier.id}/tva/comptazap`, { version: E.dossier.dossier.version })); toast("Déclarations de TVA importées depuis ComptaZap."); }
    catch (e) { toast(e.message, true); }
  },
  "import-tva": () => fenetreFichier("Récapitulatif des déclarations de TVA", "tva", "Export Excel « Récapitulatif des déclarations » de Pennylane (une ligne par case de la CA3, deux colonnes par mois)."),
  "import-paie": () => fenetreFichier("Journal de paie", "paie", "Journal de paie annuel : colonnes Code, Libellé, Salarial, Patronal. Vous pouvez aussi coller le tableau copié depuis Excel."),
  "tout-valider": b => { const cy = E.dossier.resultats.cycles.find(c => c.cle === b.dataset.cycle); cy.lignes.forEach(l => { if (!l.statut) saisir(`saisies.revision.${l.compte}.statut`, "Validé"); }); },
  "copier-mail": async () => { try { await navigator.clipboard.writeText($("#mail-texte").textContent); toast("Mail copié."); } catch (_) { toast("Copie impossible : sélectionnez le texte.", true); } },
  historique: async () => { const h = (await api("GET", `/api/dossiers/${E.dossier.dossier.id}/historique`)).historique; $("#historique").innerHTML = `<table class="t"><tbody>${h.map(x => `<tr><td class="note">${dateFr(x.quand)} ${esc(x.quand.slice(11, 16))}</td><td>${esc(x.qui)}</td><td>${esc(x.action)}</td></tr>`).join("")}</tbody></table>`; },
  supprimer: async () => { if (!confirm(`Supprimer définitivement le dossier « ${E.dossier.dossier.nom} » (clôture ${dateFr(E.dossier.dossier.cloture)}) ?`)) return; await api("DELETE", `/api/dossiers/${E.dossier.dossier.id}`); E.dossier = null; toast("Dossier supprimé."); aller("#/dossiers"); },
};

async function importerPennylane() {
  if (!E.dossier) return;
  const st = $("#etat-enregistrement"); if (st) st.textContent = "Lecture de la balance dans Pennylane…";
  try { recevoir(await api("POST", `/api/dossiers/${E.dossier.dossier.id}/balance/pennylane`, { version: E.dossier.dossier.version })); toast(`Balance importée depuis Pennylane : ${E.dossier.resultats.balance.lignes.length} comptes.`); }
  catch (e) { toast(e.message, true); if (st) st.textContent = ""; }
}

function fenetreImport() {
  const m = E.dossier.dossier;
  fenetre(`<h2>Importer la balance</h2>
    ${m.pennylane_id || m.jeton_dossier ? `<div class="carte"><h2>${ic("nuage")} Depuis Pennylane</h2><p class="note">Balance générale de l'exercice (${dateFr(m.debut_exercice)} → ${dateFr(m.cloture)}) et de l'exercice précédent. Les saisies du dossier sont conservées.</p><button class="btn primaire" id="imp-pl">Importer depuis Pennylane</button></div>` : '<p class="note">Ce dossier n\'est pas relié à Pennylane : importez un fichier.</p>'}
    <div class="carte"><h2>Depuis un fichier</h2><p class="note">Excel ou CSV : colonnes « Compte » et « Libellé », puis « Solde N » et « Solde N-1 » (ancien onglet BalanceP), ou « Débit » / « Crédit ».</p>
      <div class="grille-form"><div><label>Le fichier contient</label><select class="champ" id="imp-cible"><option value="les_deux">N et N-1 (ou N seul)</option><option value="n">Seulement N (garder le N-1 actuel)</option><option value="n1">Seulement N-1 (garder le N actuel)</option></select></div></div>
      <div class="depot" id="imp-depot" style="margin-top:10px">Déposez le fichier ici ou cliquez pour le choisir<input type="file" id="imp-fichier" accept=".xlsx,.xlsm,.csv,.txt" class="cache"></div>
      <textarea class="champ" id="imp-texte" placeholder="…ou collez ici le tableau copié depuis Excel (avec la ligne d'en-tête)" style="margin-top:8px"></textarea>
      <div id="imp-err"></div><div class="actions"><button class="btn" data-fermer>Fermer</button><button class="btn primaire" id="imp-ok">Importer le texte collé</button></div></div>`, (v, fermer) => {
    if ($("#imp-pl", v)) $("#imp-pl", v).onclick = async () => { fermer(); await importerPennylane(); };
    const envoyerFichier = async (fichier, texte) => {
      const fd = new FormData(); if (fichier) fd.append("fichier", fichier); if (texte) fd.append("texte", texte);
      fd.append("cible", $("#imp-cible", v).value); fd.append("version", E.dossier.dossier.version);
      try { recevoir(await api("POST", `/api/dossiers/${E.dossier.dossier.id}/balance/fichier`, undefined, fd)); fermer(); toast(`Balance importée : ${E.dossier.resultats.balance.lignes.length} comptes.`); }
      catch (e) { $("#imp-err", v).innerHTML = `<div class="message-erreur">${esc(e.message)}</div>`; }
    };
    zoneDepot($("#imp-depot", v), $("#imp-fichier", v), f => envoyerFichier(f));
    $("#imp-ok", v).onclick = () => { const t = $("#imp-texte", v).value; if (t.trim()) envoyerFichier(null, t); };
  });
}
function zoneDepot(zone, input, rappel) {
  zone.onclick = () => input.click();
  input.onchange = () => { if (input.files[0]) rappel(input.files[0]); };
  zone.ondragover = e => { e.preventDefault(); zone.classList.add("survol"); };
  zone.ondragleave = () => zone.classList.remove("survol");
  zone.ondrop = e => { e.preventDefault(); zone.classList.remove("survol"); if (e.dataTransfer.files[0]) rappel(e.dataTransfer.files[0]); };
}
function fenetreFichier(titre, type, aide) {
  fenetre(`<h2>${esc(titre)}</h2><p class="note">${esc(aide)}</p><div class="depot" id="f-depot">Déposez le fichier ici ou cliquez pour le choisir<input type="file" id="f-fichier" accept=".xlsx,.xlsm,.csv,.txt" class="cache"></div>
    <textarea class="champ" id="f-texte" placeholder="…ou collez le tableau copié depuis Excel" style="margin-top:8px"></textarea><div id="f-err"></div>
    <div class="actions"><button class="btn" data-fermer>Fermer</button><button class="btn primaire" id="f-ok">Importer le texte collé</button></div>`, (v, fermer) => {
    const go = async (fichier, texte) => {
      const fd = new FormData(); if (fichier) fd.append("fichier", fichier); if (texte) fd.append("texte", texte); fd.append("version", E.dossier.dossier.version);
      try { recevoir(await api("POST", `/api/dossiers/${E.dossier.dossier.id}/${type}/fichier`, undefined, fd)); fermer(); toast("Import réussi."); }
      catch (e) { $("#f-err", v).innerHTML = `<div class="message-erreur">${esc(e.message)}</div>`; }
    };
    zoneDepot($("#f-depot", v), $("#f-fichier", v), f => go(f));
    $("#f-ok", v).onclick = () => { const t = $("#f-texte", v).value; if (t.trim()) go(null, t); };
  });
}

// ---------------------------------------------------------------------------------------------------------------
// Paramètres
// ---------------------------------------------------------------------------------------------------------------
async function pageParametres() {
  E.dossier = null;
  let p = {}, cz = {};
  if (E.moi.demo) {
    $("#droite").innerHTML = `<div class="entete"><div><h1>Paramètres<span class="badge-demo">Démo</span></h1><div class="sous">Connexion à Pennylane, connecteur du poste et compte</div></div></div><div class="zone"><div class="deux">
      <div class="carte"><h2>${ic("nuage")} Pennylane</h2><p class="note">En production, Dossier Bilan lit la liste des dossiers, les exercices et les balances N et N-1 par l'API Pennylane (lecture seule ; le jeton reste sur le serveur). <b>Désactivé en mode démo</b> : aucun appel réseau.</p></div>
      <div class="carte"><h2>Connecteur du poste (ComptaZap)</h2><p class="note">En production, un petit programme installé sur le PC où tourne ComptaZap lit les PDF des déclarations de TVA déposées, contrôle chaque montant et les envoie au site. <b>Désactivé en mode démo.</b></p></div>
      <div class="carte"><h2>Mon compte</h2><p>${esc(E.moi.nom)} (${esc(E.moi.identifiant)})</p><p class="note">Compte de démonstration : pas de mot de passe à gérer. Les données de la démo sont dans <code>data-demo/</code> ; supprimez ce dossier pour repartir des dossiers d'origine.</p></div></div></div>`;
    return;
  }
  try { [p, cz] = await Promise.all([api("GET", "/api/pennylane"), api("GET", "/api/connecteur")]); } catch (e) { toast(e.message, true); }
  $("#droite").innerHTML = `<div class="entete"><div><h1>Paramètres</h1><div class="sous">Connexion à Pennylane et compte</div></div></div><div class="zone"><div class="deux">
    <div class="carte"><h2>${ic("nuage")} Pennylane</h2><p class="note">Lecture seule : l'application lit les dossiers et les balances, il n'écrit jamais dans Pennylane. Le jeton reste sur le serveur.</p>
      <div class="grille-form"><div><label>Type de jeton</label><select class="champ" id="pl-mode"><option value="cabinet" ${p.mode === "cabinet" ? "selected" : ""}>API cabinet (tout le portefeuille)</option><option value="entreprise" ${p.mode === "entreprise" ? "selected" : ""}>API entreprise (un dossier)</option></select></div>
      <div><label>Jeton ${p.jeton_present ? `(enregistré ${esc(p.jeton_fin)})` : "(aucun)"}</label><input class="champ" id="pl-jeton" type="password" placeholder="${p.jeton_present ? "Laisser vide pour garder l'actuel" : "Coller le jeton"}" autocomplete="off"></div></div>
      <div style="display:flex;gap:8px;margin-top:12px"><button class="btn primaire" id="pl-enr">Enregistrer</button><button class="btn" id="pl-test">Tester la connexion</button>${p.jeton_present ? '<button class="btn danger" id="pl-eff">Effacer le jeton</button>' : ""}</div>
      <div id="pl-res" style="margin-top:10px">${p.teste_le ? `<span class="pastille ${p.test_ok ? "ok" : "erreur"}">Dernier test le ${esc(p.teste_le)} : ${p.test_ok ? "réussi" : "échec"}</span>` : ""}</div></div>
    <div class="carte"><h2>Connecteur du poste (ComptaZap)</h2>
      <p class="note">Le site ne peut pas lire le PC où tourne ComptaZap : un petit programme installé sur ce PC lui envoie les déclarations de TVA, lues sur les PDF d'impots.gouv et contrôlées.</p>
      <table class="t"><tbody><tr><td>Poste relié</td><td>${cz.lie ? `<span class="pastille ok">Oui</span> ${esc(cz.poste || "")}` : '<span class="pastille neutre">Non</span>'}</td></tr>
      <tr><td>Dernier contact</td><td>${cz.dernier_contact ? dateFr(cz.dernier_contact) + " " + esc(cz.dernier_contact.slice(11, 16)) : "—"}</td></tr>
      <tr><td>Dernière synchro</td><td>${cz.derniere_synchro ? dateFr(cz.derniere_synchro) + " " + esc(cz.derniere_synchro.slice(11, 16)) : "—"}${cz.demande_en_attente ? ' <span class="pastille alerte">demande en attente</span>' : ""}</td></tr>
      <tr><td>Déclarations reçues</td><td>${cz.declarations || 0}${cz.non_controlees ? ` <span class="pastille alerte">${cz.non_controlees} à vérifier</span>` : ""}</td></tr>
      ${cz.erreur ? `<tr><td>Erreur</td><td><span class="pastille erreur">${esc(cz.erreur)}</span></td></tr>` : ""}</tbody></table>
      <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap"><button class="btn primaire" id="cz-code">${cz.lie ? "Nouveau code de liaison" : "Créer un code de liaison"}</button>
      ${cz.lie ? '<button class="btn" id="cz-sync">Synchroniser maintenant</button><button class="btn danger" id="cz-delier">Délier le poste</button>' : ""}</div><div id="cz-res"></div></div>
    <div class="carte"><h2>Mon compte</h2><p>${esc(E.moi.nom)} (${esc(E.moi.identifiant)})</p>${E.moi.sans_mdp
      ? `<p class="note">Sans mot de passe sur ce poste : chacun choisit son nom à l'ouverture.</p>`
      : `<div class="grille-form"><div><label>Mot de passe actuel</label><input class="champ" id="mdp-a" type="password"></div><div><label>Nouveau (10 caractères au moins)</label><input class="champ" id="mdp-n" type="password"></div></div>
      <div id="mdp-err"></div><button class="btn primaire" id="mdp-ok" style="margin-top:12px">Changer le mot de passe</button>`}</div></div></div>`;
  $("#pl-enr").onclick = async () => { try { await api("POST", "/api/pennylane", { mode: $("#pl-mode").value, jeton: $("#pl-jeton").value }); toast("Paramètres Pennylane enregistrés."); pageParametres(); } catch (e) { toast(e.message, true); } };
  $("#pl-test").onclick = async () => { $("#pl-res").innerHTML = '<span class="note">Test en cours…</span>'; try { const t = await api("POST", "/api/pennylane/test"); $("#pl-res").innerHTML = `<span class="pastille ${t.ok ? "ok" : "erreur"}">${esc(t.message)}</span>${t.apercu ? `<pre class="note" style="white-space:pre-wrap">${esc(t.apercu)}</pre>` : ""}`; } catch (e) { $("#pl-res").innerHTML = `<div class="message-erreur">${esc(e.message)}</div>`; } };
  if ($("#pl-eff")) $("#pl-eff").onclick = async () => { await api("POST", "/api/pennylane", { effacer: true }); pageParametres(); };
  $("#cz-code").onclick = async () => {
    if (cz.lie && !confirm("Le poste actuel cessera de fonctionner tant qu'il n'aura pas reçu le nouveau code. Continuer ?")) return;
    const r = await api("POST", "/api/connecteur/code");
    $("#cz-res").innerHTML = `<div class="note-correction" style="margin-top:12px"><b>Code de liaison (affiché une seule fois)</b><br><code style="user-select:all">${esc(r.code)}</code><br><br>
      Sur le PC de ComptaZap : copiez le dossier <b>connecteur</b> de Dossier Bilan, double-cliquez sur <b>installer_connecteur.bat</b>, puis collez l'adresse <code style="user-select:all">${esc(r.adresse)}</code> et ce code.</div>`;
  };
  if ($("#cz-sync")) $("#cz-sync").onclick = async () => { await api("POST", "/api/connecteur/synchroniser"); toast("Demande envoyée : le poste synchronise dans la minute."); pageParametres(); };
  if ($("#cz-delier")) $("#cz-delier").onclick = async () => { if (confirm("Délier le poste ComptaZap ?")) { await api("POST", "/api/connecteur/delier"); pageParametres(); } };
  if (!$("#mdp-ok")) return;
  $("#mdp-ok").onclick = async () => { try { await api("POST", "/api/mot-de-passe", { ancien: $("#mdp-a").value, nouveau: $("#mdp-n").value }); toast("Mot de passe changé."); $("#mdp-a").value = $("#mdp-n").value = ""; $("#mdp-err").innerHTML = ""; } catch (e) { $("#mdp-err").innerHTML = `<div class="message-erreur">${esc(e.champs ? Object.values(e.champs).join(" ") : e.message)}</div>`; } };
}

// ---------------------------------------------------------------------------------------------------------------
try { const t = localStorage.getItem("theme"); if (t) document.documentElement.dataset.theme = t; } catch (_) {}
demarrer();
