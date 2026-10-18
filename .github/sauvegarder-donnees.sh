#!/bin/bash
# =============================================================
#  Sauvegarde des données sur la branche "data"
# =============================================================
#  Utilisé par veille.yml et favoris.yml. Enregistre :
#    data/veille.db, docs/articles.json, docs/flux.xml
#  sur la branche "data", qui ne contient QUE ces trois fichiers.
#
#  La branche garde un seul commit, remplacé à chaque sauvegarde :
#  la base contient déjà tout l'historique des articles, inutile de
#  garder 2 copies par jour d'un fichier de 1,5 Mo (le dépôt grossirait
#  sans fin). Personne d'autre que les workflows n'écrit sur cette
#  branche, et ils ne tournent jamais en même temps (même groupe de
#  concurrence) : remplacer le commit est sans risque.
#  --force-with-lease refuse quand même si la branche a bougé entre-temps.
#
#  Usage : bash .github/sauvegarder-donnees.sh "message du commit"
#  Écrit change=true ou change=false dans $GITHUB_OUTPUT.
# =============================================================
set -euo pipefail

message="$1"
fichiers=(data/veille.db docs/articles.json docs/flux.xml)

sortie() {
  if [ -n "${GITHUB_OUTPUT:-}" ]; then echo "change=$1" >> "$GITHUB_OUTPUT"; fi
}

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

git fetch -q --depth=1 origin +refs/heads/data:refs/remotes/origin/data
avant="$(git rev-parse origin/data)"

# Copie de travail séparée de la branche data, pour ne pas toucher au code de main
dossier="$(mktemp -d)"
git worktree add -q --detach "$dossier" "$avant"
for fichier in "${fichiers[@]}"; do
  cp "$fichier" "$dossier/$fichier"
done

cd "$dossier"
git add "${fichiers[@]}"
if git diff --staged --quiet; then
  echo "Aucun changement : rien à sauvegarder."
  sortie false
  exit 0
fi

# Nouveau commit sans parent, qui remplace l'ancien
commit="$(git commit-tree "$(git write-tree)" -m "$message")"
git push -q --force-with-lease="data:$avant" origin "$commit:refs/heads/data"
echo "Données sauvegardées sur la branche data : $message"
sortie true
