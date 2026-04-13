# Exercice 4 — Multimodal : transcrire et analyser

## Integration dans le fil-rouge

Les capacites multimodales ont ete integrees directement dans l'agent ReAct du fil-rouge
sous forme de deux nouveaux outils :

| Fichier                      | Role                                      | API utilisee     |
|------------------------------|--------------------------------------------|------------------|
| `fil-rouge/tools/transcribe.py` | Option A — Audio → Texte → Analyse     | Whisper (whisper-1) |
| `fil-rouge/tools/vision.py`     | Option B — Image → JSON structure       | GPT-4o Vision    |

### Modification de l'agent ReAct

- `config.py` : ajout de `MODEL_VISION = "gpt-4o"` (la vision necessite gpt-4o)
- `main.py` : 2 nouveaux intents (`transcribe`, `vision`) et 2 nouvelles branches dans `executer_outil()`

L'agent detecte automatiquement quand utiliser ces outils via le schema de decision :
- *"Transcris ce fichier audio : data/sample.mp3"* → `transcribe_audio`
- *"Analyse cette facture : data/facture.jpg"* → `analyze_image`

## Tests realises

### Option A — Transcription audio

| Test | Modalite | Resultat | Qualite /5 |
|------|----------|----------|------------|
| test.m4a (vocal FR, ~15s) | Audio → Texte | Transcription exacte mot pour mot + analyse structuree | 5/5 |

**Transcription obtenue :**

> L'intelligence artificielle generative transforme le paysage technologique en 2026. Les agents autonomes capables de raisonner et d'utiliser des outils deviennent la norme dans les entreprises. La combinaison du RAG et des modeles multimodaux ouvre de nouvelles possibilites pour l'analyse des documents.

**Analyse LLM :**

- **Resume** : Impact de l'IA generative sur le paysage techno 2026, emergence des agents autonomes, combinaison RAG + multimodal
- **Points cles** : IA generative, agents autonomes en entreprise, RAG + multimodal pour l'analyse documentaire
- **Langue/ton** : Technique et formel

```bash
cd fil-rouge
.venv/bin/python3 -c "from tools.transcribe import transcrire_audio; import json; r = transcrire_audio('../test.m4a'); print(json.dumps(r, ensure_ascii=False, indent=2))"
```

### Option B — Analyse d'image/PDF

| Test | Modalite | Resultat | Qualite /5 |
|------|----------|----------|------------|
| test.pdf (article Clubic) | PDF → JSON | Extraction complete : titre, auteur, date, montants, investisseurs | 5/5 |

**JSON extrait :**

```json
{
  "type_document": "autre",
  "titre": "SiFive : NVIDIA prepare son cheval de troie dans l'ecosysteme ouvert RISC-V",
  "auteur": "Naim Bada",
  "date_publication": "13 avril 2026",
  "resume": "SiFive vient de lever 400M$ avec NVIDIA parmi les investisseurs...",
  "montant_leve": "400 millions de dollars",
  "valorisation": "3,65 milliards",
  "investisseurs": ["NVIDIA", "Apollo Global Management", "Point72", "T. Rowe Price", "Atreides Management"],
  "source": "clubic.com"
}
```

```bash
cd fil-rouge
.venv/bin/python3 -c "from tools.vision import analyser_image; import json; r = analyser_image('../test.pdf'); print(json.dumps(r, ensure_ascii=False, indent=2))"
```

## Reflexion

> "Pour mon projet, le multimodal pourrait servir a..."
>
> - Transcrire des podcasts/conferences tech et les integrer dans la veille (audio → articles)
> - Analyser des screenshots d'interfaces ou de dashboards partages sur les flux RSS
> - Extraire des donnees de rapports PDF scannes (images de tableaux, graphiques)
