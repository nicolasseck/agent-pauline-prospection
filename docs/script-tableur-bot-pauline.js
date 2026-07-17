// --- CONFIGURATION DE LA STRUCTURE DU TABLEAU ---
const CONFIG_COL_A = {
  1: "Variable",
  2: "section_activite_principale",
  3: "tranche_effectif_salarie",
  4: "categorie_entreprise",
  5: "etat_administratif",
  6: "departements_cible",
  7: "objectif_par_run",
  8: "seuil_retention",
  9: "injecter_pipedrive",
  10: "exclure_procedure_collective",
  11: "notifier"
};

const CONFIG_COL_C = {
  1: "Description",
  2: "Sections NAF ciblées (E=déchets, F=BTP, H=transport, I=HCR, N=intérim/propreté/sécurité, Q=santé).",
  3: "Codes INSEE de tranche d'effectif ciblés (50 salariés et plus).",
  4: "Catégories d'entreprise ciblées.",
  5: "A = entreprises actives uniquement.",
  6: "Départements parcourus tour à tour (un par exécution), séparés par des virgules.",
  7: "Nombre de nouveaux prospects visés par exécution.",
  8: "Score minimum pour garder un prospect. Laisser VIDE = garder tous les prospects.",
  9: "Oui/Non — injecter les prospects retenus dans Pipedrive.",
  10: "Oui/Non — exclure les entreprises en procédure collective (BODACC).",
  11: "Oui/Non — envoyer le récapitulatif de fin d'exécution."
};

// --- CONFIGURATION DES VALEURS AUTORISÉES (COLONNE B) ---
const OPTIONS_COL_B = {
  2: {
    autorisees: ["A","B", "C", "D", "E", "F", "H", "I","J" , "K", "L", "M",  "N","O" , "P", "Q", "R", "S", "T", "U"],
    defaut: "E,F,H,I,N,Q",
    msg: "Les valeurs saisies à la ligne 2 doivent faire partie de la liste : A,B,C,D,E,F,H,I,J,K,L,M,N,O,P,Q,R,S,T,U (séparées par des virgules sans espace)."
  },
  3: {
    autorisees: ["NN", "00", "01", "02","03","11","12","21","22","31","32","42","51","52","53"],
    defaut: "21,22,31,32,41,42,51,52,53",
    msg: "Les valeurs saisies à la ligne 3 doivent faire partie de la liste : NN,00,01,02,03,11,12,21,22,31,32,42,51,52,53 (séparées par des virgules sans espace)."
  },
  4: {
    autorisees: ["PME", "ETI", "GE"],
    defaut: "PME,ETI,GE",
    msg: "Les valeurs saisies à la ligne 4 doivent faire partie de la liste : PME,ETI,GE (séparées par des virgules sans espace)."
  },
  5: {
    autorisees: ["A", "C"],
    defaut: "A",
    msg: "Les valeurs saisies à la ligne 5 doivent être : A ou C."
  },
  6: {
    autorisees: [
      "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
      "11", "12", "13", "14", "15", "16", "17", "18", "19", "2A",
      "2B", "21", "22", "23", "24", "25", "26", "27", "28", "29",
      "30", "31", "32", "33", "34", "35", "36", "37", "38", "39",
      "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
      "50", "51", "52", "53", "54", "55", "56", "57", "58", "59",
      "60", "61", "62", "63", "64", "65", "66", "67", "68", "69",
      "70", "71", "72", "73", "74", "75", "76", "77", "78", "79",
      "80", "81", "82", "83", "84", "85", "86", "87", "88", "89",
      "90", "91", "92", "93", "94", "95", "971", "972", "973", "974", "976"
    ],
    defaut: "75,92,93,94,77,78,91,95,971,972,973,974,975,976",
    msg: "Les valeurs saisies à la ligne 6 doivent être des départements français ou DOM-TOM valides, séparés par des virgules sans espace."
  }
};

/**
 * Modifie la valeur d'une cellule si elle est vide ou si elle ne correspond pas à la structure.
 * 
 * @param {GoogleAppsScript.Events.SheetsOnEdit} e - Événement du tableur 
 */
function onEdit(e) {
  const classeur = e.source;
  const feuille = classeur.getActiveSheet();
  const plageModifiee = e.range;

  if (feuille.getName() !== "Paramétrage") {
    return;
  }

  const nbLignes = plageModifiee.getNumRows();
  const nbColonnes = plageModifiee.getNumColumns();

  for (let i = 1; i <= nbLignes; i++) {
    for (let j = 1; j <= nbColonnes; j++) {
      
      const celluleActuelle = plageModifiee.getCell(i, j);
      const col = celluleActuelle.getColumn();
      const lig = celluleActuelle.getRow();
      const valeurSaisie = String(celluleActuelle.getValue()).trim();

      // --- FORMATTAGE HARMONISÉ DE L'EN-TÊTE (Ligne 1) ---
      if (lig === 1 && col <= 3) {
        celluleActuelle.setBackground("#1f4e78");
        celluleActuelle.setFontColor("#FFFFFF");
        celluleActuelle.setFontWeight("bold");
      }

      // --- COLONNE A (VARIABLES SYSTEME) ---
      if (col === 1) {
        const valeurAttendue = CONFIG_COL_A[lig];
        if (valeurAttendue && valeurSaisie !== valeurAttendue) {
          celluleActuelle.setValue(valeurAttendue);
        }
      }

      // --- COLONNE B (SAISIE DES VALEURS) ---
      else if (col === 2) {
        // En-tête de la colonne B
        if (lig === 1) {
          if (valeurSaisie !== "Valeur") {
            celluleActuelle.setValue("Valeur");
          }
        }
        // Cas des lignes à options multiples (Lignes 2, 3, 4, 5, 6)
        else if (OPTIONS_COL_B[lig]) {
          const config = OPTIONS_COL_B[lig];
          if (valeurSaisie === "") {
            celluleActuelle.setValue(config.defaut);
          } else if (!checkValue(valeurSaisie, config.autorisees)) {
            afficherAlerte(config.msg);
            celluleActuelle.setValue(config.defaut);
          }
        }
        // Cas de la ligne 7 (Objectif par run - Doit être un entier)
        else if (lig === 7) {
          const valeurNum = Number(valeurSaisie);
          if (valeurSaisie === "") {
            celluleActuelle.setValue(50);
          } else if (isNaN(valeurNum) || !Number.isInteger(valeurNum)) {
            afficherAlerte("La ligne 7 n'accepte que des nombres entiers (ex: 50).");
            celluleActuelle.setValue(50);
          }
        }
        // Cas de la ligne 8 (Seuil de rétention - Peut être vide)
        else if (lig === 8) {
          // Rien à faire si vide..
        }
        // Cas des lignes booléennes (Lignes 9, 10, 11)
        else if (lig >= 9 && lig <= 11) {
          if (valeurSaisie === "") {
            celluleActuelle.setValue("Oui");
          } else if (valeurSaisie !== "Oui" && valeurSaisie !== "Non") {
            afficherAlerte(`Les valeurs saisies aux lignes 9, 10 et 11 doivent être exclusivement "Oui" ou "Non".`);
            celluleActuelle.setValue("Oui");
          }
        }
      }

      // --- COLONNE C (DESCRIPTIONS SYSTEME) ---
      else if (col === 3) {
        const valeurAttendue = CONFIG_COL_C[lig];
        if (valeurAttendue && valeurSaisie !== valeurAttendue) {
          celluleActuelle.setValue(valeurAttendue);
        }
      }

    }
  }
}

/**
 * Vérifie si tous les éléments d'une chaîne séparés par des virgules
 * appartiennent à la liste des valeurs autorisées.
 * 
 * @param {string} string - Chaîne de caractères à tester.
 * @param {string[]} pattern - Tableau des patterns acceptés.
 * @return {boolean}
 */
function checkValue(string, pattern) {
  if (!string) return false;
  const listeString = string.split(',');
  for (let i = 0; i < listeString.length; i++) {
    const element = listeString[i].trim();
    if (element === "" || !pattern.includes(element)) {
      return false;
    }
  }
  return true;
}

/**
 * Encapsule l'appel de l'interface utilisateur pour afficher une alerte.
 * 
 * @param {string} message - Message à afficher dans la pop-up.
 */
function afficherAlerte(message) {
  try {
    const ui = SpreadsheetApp.getUi();
    ui.alert("Saisie incorrecte", message, ui.ButtonSet.OK);
  } catch (err) {
    // Évite de faire planter le script si exécuté hors interface utilisateur (ex: tests manuels)
    Logger.log("Alerte utilisateur : " + message);
  }
}