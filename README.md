

# AI4FoodDB – RDF Triple Generation

This project converts the **AI4FoodDB CSV datasets** into **RDF triples** using a custom ontology built in WebProtégé.  
The goal is to create a **machine-readable knowledge graph** that connects participant, health, lifestyle, and wearable data.

---

## Project structure

ai4fooddb/
├── data/               # Input CSV files
├── ontology/           # WebProtégé ontology (.ttl)
├── src/
│   ├── make_triples.py     # Builds triples for one dataset
│   └── generate_all.py     # Runs make_triples.py for all CSVs
├── ai4food_triples.ttl     # Output knowledge graph
└── README.md

---

## How it works

1. **`make_triples.py`** reads one CSV + the ontology and creates RDF triples.  
2. **`generate_all.py`** runs this automatically for every CSV in `data/`.  
3. All triples are merged into one file: `ai4food_triples.ttl`.

---

## Run the pipeline

```bash
pip install rdflib pyyaml

Then run the full pipeline:

python src/generate_all.py

This will:
	•	Parse all .csv files in the data/ folder
	•	Match their columns to ontology properties
	•	Write the combined RDF graph to ai4food_triples.ttl

⸻

Notes
	•	Missing ontology labels are skipped automatically.

