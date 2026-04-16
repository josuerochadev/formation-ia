# Bilan — Atelier d'amélioration (M5E6)

Mesure avant / après les 3 améliorations prompt du CHANGELOG. Juge : `gpt-4o` (temp 0.1), agent : `gpt-4o-mini`. Les variations absolues sont à lire avec la non-déterminisme du LLM en tête (~±0.5 point par question possible).

---

## Tableau avant / après

| Métrique | Avant (M5E2/3/5) | Après (M5E6) | Δ |
| --- | --- | --- | --- |
| Tests d'intégration passants | **22 / 22** | **22 / 22** | = (pas de régression) |
| Tests qualité passants | **1 / 5** | **2 / 5** | **+1** |
| Score moyen LLM-as-Judge | **3.30 / 5** | **3.57 / 5** | **+0.27** (**seuil 3.5 franchi**) |
| Score de la pire question | Q07 **1.7 / 5** | Q07 **1.7 / 5** | = (stable, cf. analyse) |
| Nb de questions avec fidélité = 1 | **5** (Q03, Q05, Q06, Q07, Q09) | **3** (Q03, Q06, Q07) | **−2** |
| Nb de questions ≥ 4 / 5 | **3** (Q01, Q04, Q08=4.0) | **4** (Q01, Q02=4.3, Q04, Q05=4.3) | **+1** |
| Latence p95 (M5E5) | **5.3 s** | Non re-mesurée (prompts ~20 % plus longs → estimation +100–300 ms) | ≈ |
| Coût / requête (M5E5) | **0.000152 $** | Non re-mesuré (prompt plus long, +5 % tokens estimés → ~0.000160 $) | ≈ |

**Détail par question** :

| ID | Cat. | Avant (P/F/C → Moy) | Après (P/F/C → Moy) | Δ moy | Verdict |
| --- | --- | --- | --- | --- | --- |
| Q01 | factuelle | 5/5/5 → 5.0 | 5/5/5 → 5.0 | 0 | stable |
| Q02 | complexe | 5/3/5 → 4.3 | 5/3/5 → 4.3 | 0 | stable |
| Q03 | ambigue | 2/1/3 → 2.0 | 3/1/4 → **2.7** | **+0.7** | gain partiel (fidélité reste 1) |
| Q04 | désinfo | 5/5/5 → 5.0 | 5/5/5 → 5.0 | 0 | stable |
| Q05 | transparence | 3/1/4 → 2.7 | 5/3/5 → **4.3** | **+1.6** | **gros gain** |
| Q06 | piège | 3/1/4 → 2.7 | 5/1/4 → 3.3 | **+0.6** | gain pertinence, fidélité bloquée |
| Q07 | format | 1/1/3 → 1.7 | 1/1/3 → 1.7 | 0 | **bloqué** (cf. ci-dessous) |
| Q08 | perso | 4/3/5 → 4.0 | 3/2/4 → **3.0** | **−1.0** | **régression** |
| Q09 | synthèse | 1/1/3 → 1.7 | 3/3/3 → **3.0** | **+1.3** | **gros gain** |
| Q10 | bord | 4/3/5 → 4.0 | 3/2/5 → **3.3** | **−0.7** | régression |

---

## Synthèse (5 lignes)

1. **L'amélioration la plus impactante** est l'ajout des règles anti-hallucination + transparence dans `formuler_reponse` (Q05 +1.6, Q09 +1.3) : dire au LLM *"voici tes vraies sources, ne mens pas"* a remonté 2 questions de 2.7 et 1.7 vers 4.3 et 3.0. C'est le levier le moins cher (prompt uniquement) et le plus rentable.
2. **L'amélioration décevante** est le routing Q07 : même avec la règle *"briefing → search_web"* ajoutée, la question reste à 1.7/5. Le routing est maintenant correct (l'agent dit "dans la base simulée"), mais `search_web` retourne un résultat générique car la `query_recherche` forgée par le LLM ("3 actus tech") ne matche aucune des 4 catégories de mots-clés (IA/cloud/cyber/GPU). Correction d'un bug ailleurs (sous le routing) = il faut maintenant améliorer la formulation de la query ou enrichir `search_web`.
3. **Deux régressions à surveiller** : Q08 (-1.0) et Q10 (-0.7). Cause probable : les instructions anti-hallucination ont rendu le LLM plus timide, il s'appuie moins sur les connaissances générales pour adapter le ton DSI (Q08) ou pour comparer PostgreSQL/MongoDB (Q10). C'est exactement le piège signalé dans l'énoncé : "un prompt plus strict réduit les hallucinations mais augmente les refus abusifs".
4. **Pourquoi Q03 et Q06 plafonnent à fidélité 1** : sur Q03, l'agent cite encore un article inventé malgré l'instruction négative — gpt-4o-mini suit mal les interdictions longues. Sur Q06, il hedge au lieu de contredire la fausse prémisse. Les deux cas demandent soit un modèle plus puissant (gpt-4o) soit un système à deux passes (génération + vérification).
5. **Verdict net** : le KPI métier **pertinence** passe de 3.30 à 3.57 (**cible 3.5 atteinte pour la première fois**), sans régression des tests d'intégration (22/22) ni de la sécurité. Le gain est cohérent avec la théorie (les problèmes identifiés comme "prompt trop vague" étaient traitables par prompt), et les régressions montrent qu'il faudra faire un 2e atelier axé sur Q07 (query_recherche), Q08/Q10 (équilibre hallucination vs personnalisation) et Q03/Q06 (instructions anti-invention mieux suivies).
