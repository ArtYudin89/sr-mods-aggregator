#!/usr/bin/env bash
# Пуш коммитов прогона в master с повторами: при отказе — fetch + rebase на свежий
# origin/master. Код выхода не 0, если пуш так и не прошёл или rebase упёрся в конфликт:
# раньше цикл в workflow всегда кончался успехом, и прогон «success» молча терял свои
# коммиты (SR-67, 26.10.2026: CONFLICT в state/lock.json — прогон зелёный).
set -u
for i in 1 2 3; do
  git push origin HEAD:master && exit 0
  echo "push retry $i (fetch+rebase)"
  git fetch origin master || continue
  if ! git rebase origin/master; then
    git status --short | head -20
    git rebase --abort
    echo "::error::rebase на origin/master: конфликт — коммиты прогона НЕ запушены"
    exit 1
  fi
done
echo "::error::push в master не прошёл после 3 попыток — коммиты прогона НЕ запушены"
exit 1
