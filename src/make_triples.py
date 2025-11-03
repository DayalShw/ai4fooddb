
import argparse
import pandas as pd
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD
from rdflib.namespace import SKOS, DCTERMS


# -------------------------------
# Ontology loader
# -------------------------------
class Ontology:
    def __init__(self, path_or_url: str, parse_format: str | None = None):
        self.g = Graph()
        self.g.parse(path_or_url, format=parse_format)
        self.RDF, self.RDFS, self.OWL, self.XSD = RDF, RDFS, OWL, XSD
        self.SKOS, self.DCTERMS = SKOS, DCTERMS

    def label(self, iri: URIRef) -> str:
        for p in (RDFS.label, SKOS.prefLabel, DCTERMS.title):
            lab = self.g.value(iri, p, any=False)
            if lab:
                return str(lab)
        s = str(iri)
        return s.split("#")[-1] if "#" in s else s.rsplit("/", 1)[-1]

    def resolve_by_label(self, text: str):
        """Find ontology element by label (case-insensitive)."""
        txt = text.strip().lower()
        for p in (RDFS.label, SKOS.prefLabel, DCTERMS.title):
            for s, _, o in self.g.triples((None, p, None)):
                if hasattr(o, "language") and o.language and o.language != "en":
                    continue
                if str(o).strip().lower() == txt:
                    return s
        return None

    def ranges(self, prop: URIRef):
        return list(self.g.objects(prop, RDFS.range))


# -------------------------------
# Datatype coercion helpers
# -------------------------------
def coerce_literal(value):
    """Fallback typing: int → integer, float → double, else string."""
    if pd.isna(value):
        return None
    try:
        if str(value).strip().isdigit():
            return Literal(int(value), datatype=XSD.integer)
        float_val = float(value)
        return Literal(float_val, datatype=XSD.double)
    except Exception:
        return Literal(str(value), datatype=XSD.string)


def coerce_by_range(value, ranges):
    """Try to coerce according to ontology-declared range."""
    if pd.isna(value):
        return None
    for r in ranges:
        if r in [XSD.integer, XSD.int, XSD.long, XSD.short]:
            try:
                return Literal(int(value), datatype=r)
            except Exception:
                continue
        if r in [XSD.double, XSD.decimal, XSD.float]:
            try:
                return Literal(float(value), datatype=r)
            except Exception:
                continue
        if r == XSD.boolean:
            return Literal(str(value).strip().lower() in ("1", "true", "yes", "y"), datatype=XSD.boolean)
        if r == XSD.string:
            return Literal(str(value), datatype=XSD.string)
    # fallback
    return coerce_literal(value)


# -------------------------------
# Graph builder
# -------------------------------
def build_graph(ontology_path: str,
                csv_path: str,
                base_iri: str,
                class_label: str,
                column_to_property_label: dict[str, str],
                subject_column: str | None = None) -> Graph:

    onto = Ontology(ontology_path)
    g = Graph()

    # Resolve class
    class_iri = onto.resolve_by_label(class_label)
    if not class_iri:
        raise ValueError(f"Class label not found in ontology: {class_label}")

    # Resolve properties
    col_to_prop_iri = {}
    prop_ranges = {}
    for col, prop_label in column_to_property_label.items():
        iri = onto.resolve_by_label(prop_label)
        if not iri:
            print(f"⚠️  Skipping column '{col}': ontology label not found '{prop_label}'")
            continue
        col_to_prop_iri[col] = iri
        prop_ranges[iri] = onto.ranges(iri)

    # Read CSV
    df = pd.read_csv(csv_path)

    # Build triples
    for i, row in df.iterrows():
        if subject_column and pd.notna(row.get(subject_column)):
            subj = URIRef(f"{base_iri}{row[subject_column]}")
        else:
            subj = URIRef(f"{base_iri}{i+1}")

        g.add((subj, RDF.type, class_iri))

        for col, prop_iri in col_to_prop_iri.items():
            if col not in df.columns:
                continue
            val = row[col]
            lit = coerce_by_range(val, prop_ranges.get(prop_iri, []))
            if lit is not None:
                g.add((subj, prop_iri, lit))

    return g


# -------------------------------
# CLI entry point
# -------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Generate RDF triples directly from CSV using WebProtégé ontology (.ttl/.owl)"
    )
    parser.add_argument("--ontology", required=True, help="Path or URL to ontology file (.ttl/.owl)")
    parser.add_argument("--csv", required=True, help="Input CSV file path")
    parser.add_argument("--base", required=True, help="Base IRI for instances")
    parser.add_argument("--class-label", required=True, help="Ontology class label for each CSV row")
    parser.add_argument("--subject-column", default=None, help="CSV column for subject ID")
    parser.add_argument("--map", nargs="+", metavar="COL=PROP_LABEL",
                        help="Column-to-property mappings (e.g., Age=age BMI='body mass index')")
    parser.add_argument("--out", default="out.ttl", help="Output Turtle file")
    args = parser.parse_args()

    # Parse mappings
    mapping = {}
    if args.map:
        for kv in args.map:
            if "=" not in kv:
                raise SystemExit(f"Bad mapping '{kv}'. Use COL=PROP_LABEL.")
            k, v = kv.split("=", 1)
            mapping[k] = v.strip().strip("'").strip('"')

    g = build_graph(
        ontology_path=args.ontology,
        csv_path=args.csv,
        base_iri=args.base,
        class_label=args.class_label,
        column_to_property_label=mapping,
        subject_column=args.subject_column,
    )

    g.serialize(args.out, format="turtle")
    print(f"\n✅ RDF triples written to: {args.out}\n")
    print(f"Total triples: {len(g)}")


if __name__ == "__main__":
    main()