#!/usr/bin/env python3
import argparse, csv, sys
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
import yaml

# ---------- utils ----------
class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"  # keep placeholder visible if missing

def coerce_literal(val, dtype_str):
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() in {"nan", "none"}:
        return None

    if dtype_str.endswith("string"):
        return Literal(s, datatype=XSD.string)
    if dtype_str.endswith("boolean"):
        truthy = {"true","1","yes","y","t"}
        falsy  = {"false","0","no","n","f"}
        low = s.lower()
        if low in truthy:  return Literal(True, datatype=XSD.boolean)
        if low in falsy:   return Literal(False, datatype=XSD.boolean)
        # fallback: try int/float, else string -> boolean not safe; store as string
        return Literal(s, datatype=XSD.string)
    if dtype_str.endswith("integer"):
        try:
            return Literal(int(float(s)), datatype=XSD.integer)
        except Exception:
            return Literal(s, datatype=XSD.string)
    if dtype_str.endswith("float") or dtype_str.endswith("double") or dtype_str.endswith("decimal"):
        try:
            return Literal(float(s), datatype=XSD.float)
        except Exception:
            return Literal(s, datatype=XSD.string)
    # default
    return Literal(s)

def build_subject(base_iri, template, row):
    # Allow {id} etc. If a key is missing, leave the {key} in place (visible)
    formatted = template.format_map(SafeDict(**row))
    # Replace spaces and unsafe chars lightly
    safe = "".join(c if c.isalnum() or c in "_-." else "_" for c in formatted)
    return URIRef(base_iri + safe)

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Deterministic RDF generator for AI4FoodDB")
    ap.add_argument("--mapping", required=True, help="Path to mapping.yaml")
    ap.add_argument("--out", required=True, help="Output RDF file (e.g., ai4food_triples.ttl)")
    ap.add_argument("--format", default="turtle", choices=["turtle","xml","nt","n3","trig"], help="Serialization format")
    args = ap.parse_args()

    cfg_path = Path(args.mapping)
    if not cfg_path.exists():
        print(f"ERROR: mapping file not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    cfg = yaml.safe_load(cfg_path.read_text())

    base_iri = cfg.get("base_iri", "http://example.org/ai4food/")
    prefixes = cfg.get("prefixes", {"ex": base_iri, "xsd": str(XSD)})
    ontology_path = cfg.get("ontology_path")

    g = Graph()

    # Bind prefixes
    for pfx, iri in prefixes.items():
        try:
            g.bind(pfx, Namespace(iri))
        except Exception:
            g.bind(pfx, iri)

    # Load ontology (if present)
    if ontology_path:
        onto_file = Path(ontology_path)
        if onto_file.exists():
            try:
                g.parse(onto_file, format="turtle")
                print(f"Loaded ontology: {ontology_path}")
            except Exception as e:
                print(f"WARNING: could not parse ontology {ontology_path}: {e}", file=sys.stderr)
        else:
            print(f"WARNING: ontology file not found: {ontology_path}", file=sys.stderr)

    EX = Namespace(prefixes.get("ex", base_iri))

    rows_processed = 0
    value_triples = 0
    datasets = cfg.get("datasets", [])

    for block in datasets:
        name = block.get("name", "<unnamed>")
        path = Path(block.get("path", ""))
        id_col = block.get("id_column")
        subj_template = block.get("subject_template", "Row_{id}")
        rdf_types = block.get("rdf_types", [])
        pred_map = block.get("predicate_map", {})

        if not path.exists():
            print(f"Skipping missing dataset: {path}")
            continue

        print(f"Processing dataset: {name} <- {path.name}")
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows_processed += 1

                # Subject
                subj = build_subject(base_iri, subj_template, row)

                # Types
                for t in rdf_types:
                    # t like "ex:biomarkers" or full IRI
                    if ":" in t and not t.startswith("http"):
                        pfx, local = t.split(":", 1)
                        ns = prefixes.get(pfx)
                        if ns:
                            g.add((subj, RDF.type, URIRef(ns + local)))
                            value_triples += 1
                            continue
                    g.add((subj, RDF.type, URIRef(t)))
                    value_triples += 1

                # Predicates
                for col, spec in pred_map.items():
                    # spec can be {"predicate": "...", "datatype": "..."}
                    if isinstance(spec, dict):
                        pred_str = spec.get("predicate")
                        dtype_str = spec.get("datatype", "xsd:string")
                    else:
                        # allow shorthand string predicate
                        pred_str = str(spec)
                        dtype_str = "xsd:string"

                    if pred_str is None:
                        continue

                    raw_val = row.get(col)
                    lit = coerce_literal(raw_val, dtype_str)
                    if lit is None:
                        continue

                    # Resolve qname predicate like ex:height_cm
                    if ":" in pred_str and not pred_str.startswith("http"):
                        pfx, local = pred_str.split(":", 1)
                        ns = prefixes.get(pfx)
                        if ns:
                            pred_uri = URIRef(ns + local)
                        else:
                            pred_uri = URIRef(pred_str)  # fallback
                    else:
                        pred_uri = URIRef(pred_str)

                    g.add((subj, pred_uri, lit))
                    value_triples += 1

    # Write out
    out_path = Path(args.out)
    g.serialize(destination=out_path, format=args.format)
    print(f"Done. Rows processed: {rows_processed}. Value triples: {value_triples}.")
    print(f"Wrote RDF → {out_path} (format: {args.format}).")

if __name__ == "__main__":
    main()
