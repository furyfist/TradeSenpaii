import re
import pandas as pd
from pathlib import Path

# CONFIG
INPUT_CSV  = Path("data/processed/sec_sentiment_input.csv")
OUTPUT_CSV = Path("data/processed/sec_sentiment_features.csv")

# LOUGHRAN-McDONALD DICTIONARY
# Source: https://sraf.nd.edu/loughranmcdonald-master-dictionary/
# These are the core word lists from the 2011 paper
# "When Is a Liability Not a Liability?" — Journal of Finance
LM_POSITIVE = {
    "able", "abundant", "acclaimed", "achieve", "acumen", "adaptable",
    "adequate", "admirable", "advancement", "advantage", "advantaged",
    "beneficial", "best", "better", "bolster", "boom", "breakthrough",
    "brilliant", "capital", "celebrate", "clarity", "collaborate",
    "committed", "competitive", "confidence", "confident", "consistent",
    "constructive", "creative", "deliver", "dependable", "dominant",
    "driven", "durable", "dynamic", "efficient", "empower", "enhance",
    "enjoy", "enrich", "ensure", "enthusiasm", "excellent", "exceptional",
    "expand", "expertise", "favorable", "flexibility", "flourish",
    "focused", "formidable", "gain", "good", "growth", "high", "ideal",
    "improve", "improved", "improvement", "income", "increase", "increased",
    "innovative", "integrated", "leading", "leverage", "long-term",
    "loyal", "momentum", "notable", "optimism", "optimistic", "outperform",
    "outstanding", "position", "positive", "premium", "proactive",
    "productive", "profitability", "profitable", "progress", "promising",
    "quality", "reach", "reliable", "resilient", "robust", "stable",
    "strategic", "streamline", "strength", "strengthen", "strong",
    "success", "successful", "superior", "sustainable", "transformative",
    "upward", "valuable", "value", "well", "win"
}

LM_NEGATIVE = {
    "abnormal", "adverse", "against", "allegation", "bankrupt", "below",
    "breach", "burden", "challenge", "charges", "claim", "closure",
    "complaint", "concern", "constrain", "costly", "crime", "crisis",
    "critical", "damage", "decline", "decrease", "default", "deficiency",
    "deficit", "delay", "deteriorate", "difficult", "difficulty",
    "diminish", "dispute", "disrupt", "distress", "downturn", "drop",
    "fail", "failure", "fall", "falling", "fault", "fine", "forfeit",
    "fraud", "harm", "heavy", "impair", "impairment", "inadequate",
    "insufficient", "investigation", "judgment", "lawsuit", "layoff",
    "liability", "litigation", "loss", "losses", "lower", "misstate",
    "negative", "negligence", "noncompliance", "obstacle", "operating loss",
    "penalty", "problem", "prosecution", "recall", "reduce", "reduced",
    "reduction", "regulatory", "reject", "restated", "restatement",
    "restructure", "risk", "serious", "setback", "severe", "shortage",
    "significant loss", "substandard", "suspect", "terminate", "trouble",
    "unable", "uncertain", "underperform", "unfavorable", "unresolved",
    "unsatisfactory", "violation", "warn", "warning", "weak", "weakness",
    "worse", "writedown", "writeoff", "wrong"
}

LM_UNCERTAIN = {
    "allegedly", "appear", "appears", "approximately", "around",
    "assume", "assumption", "believe", "believed", "can", "concern",
    "conditional", "contingent", "could", "depend", "depends",
    "doubt", "doubtful", "estimate", "estimated", "expect", "expected",
    "exposure", "fluctuate", "generally", "if", "indefinite", "indicate",
    "intend", "likely", "may", "maybe", "might", "nearly", "no assurance",
    "not certain", "objective", "outlook", "pending", "perhaps", "plan",
    "possible", "possibly", "potential", "potentially", "predict",
    "projected", "propose", "roughly", "seek", "seem", "should",
    "sometime", "suggest", "tentative", "uncertain", "uncertainty",
    "unclear", "unexpected", "unknown", "unlikely", "variable", "whether",
    "would"
}

LM_LITIGIOUS = {
    "adjudicate", "allegation", "allege", "alleged", "appeal", "arbitrat",
    "assert", "breach", "case", "claim", "claimant", "class action",
    "compensat", "complainant", "complaint", "comply", "contempt",
    "conviction", "counterclaim", "court", "criminal", "damages",
    "defendant", "defend", "deposition", "dispute", "enforcement",
    "enjoin", "evidence", "fine", "fraud", "guilty", "hearing",
    "indemnif", "injunction", "judgment", "judicial", "jurisdiction",
    "lawsuit", "legal", "liable", "litigation", "malpractice", "mediation",
    "negligence", "obligation", "penalty", "plaintiff", "plead",
    "proceeding", "prosecut", "regulatory", "remedy", "sanction",
    "settlement", "statute", "subpoena", "sue", "suit", "summon",
    "testimony", "trial", "tribunal", "verdict", "violation"
}

LM_CONSTRAINING = {
    "binding", "bounded", "cannot", "clause", "compelled", "comply",
    "compulsory", "conditional", "confine", "constrain", "constraint",
    "contingent", "covenant", "deadline", "depend", "impose", "imposed",
    "limit", "limitation", "limited", "mandate", "mandated", "mandatory",
    "must", "necessary", "obligation", "oblige", "prohibit", "require",
    "required", "requirement", "requires", "restrict", "restriction",
    "restrictive", "shall", "subject to", "threshold"
}


# TOKENIZER — simple, fast, no external deps
def tokenize(text: str) -> list:
    """Lowercase and split into words, strip punctuation."""
    text  = text.lower()
    words = re.findall(r"\b[a-z][a-z\-]*[a-z]\b", text)
    return words


# SCORE ONE FILING
def score_filing(text: str) -> dict:
    words       = tokenize(text)
    total_words = len(words)

    if total_words == 0:
        return {
            "lm_positive":       0,
            "lm_negative":       0,
            "lm_uncertain":      0,
            "lm_litigious":      0,
            "lm_constraining":   0,
            "lm_pos_pct":        0.0,
            "lm_neg_pct":        0.0,
            "lm_uncertain_pct":  0.0,
            "lm_sentiment_score":0.0,
            "total_words":       0
        }

    pos_count  = sum(1 for w in words if w in LM_POSITIVE)
    neg_count  = sum(1 for w in words if w in LM_NEGATIVE)
    unc_count  = sum(1 for w in words if w in LM_UNCERTAIN)
    lit_count  = sum(1 for w in words if w in LM_LITIGIOUS)
    con_count  = sum(1 for w in words if w in LM_CONSTRAINING)

    # Normalized percentages — comparable across long and short filings
    pos_pct    = round(pos_count  / total_words * 100, 4)
    neg_pct    = round(neg_count  / total_words * 100, 4)
    unc_pct    = round(unc_count  / total_words * 100, 4)

    # Core sentiment signal: (positive - negative) / total
    # Positive = stock likely to rise, Negative = likely to fall
    sentiment  = round((pos_count - neg_count) / total_words * 100, 4)

    return {
        "lm_positive":        pos_count,
        "lm_negative":        neg_count,
        "lm_uncertain":       unc_count,
        "lm_litigious":       lit_count,
        "lm_constraining":    con_count,
        "lm_pos_pct":         pos_pct,
        "lm_neg_pct":         neg_pct,
        "lm_uncertain_pct":   unc_pct,
        "lm_sentiment_score": sentiment,
        "total_words":        total_words
    }


# MAIN
def run_lm_sentiment():
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_CSV)
    print(f"[INFO] Scoring {len(df)} filings with Loughran-McDonald...")

    records = []
    for i, row in df.iterrows():
        scores = score_filing(str(row["clean_text"]))
        records.append({
            "date":             row["date"],
            "form_type":        row["form_type"],
            "accession_number": row["accession_number"],
            **scores
        })

        if (i + 1) % 100 == 0:
            print(f"  [PROGRESS] {i+1}/{len(df)} scored...")

    output_df = pd.DataFrame(records)
    output_df["date"] = pd.to_datetime(output_df["date"])
    output_df = output_df.sort_values("date").reset_index(drop=True)
    output_df.to_csv(OUTPUT_CSV, index=False)

    print(f"\n[DONE] Saved to {OUTPUT_CSV}")
    print(f"\n[SCORE STATS]")
    print(output_df["lm_sentiment_score"].describe())
    print(f"\n[SAMPLE]")
    print(output_df[["date","form_type","lm_pos_pct","lm_neg_pct",
                      "lm_uncertain_pct","lm_sentiment_score"]].head(10).to_string(index=False))


if __name__ == "__main__":
    run_lm_sentiment()