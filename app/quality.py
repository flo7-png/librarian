"""
Quality gate on extracted text
"""
import os
import logging
import re
from typing import Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Configuration
QUALITY_THRESHOLD = float(os.getenv("QUALITY_THRESHOLD", "0.35"))
MIN_CHARS = int(os.getenv("QUALITY_MIN_CHARS", "50"))
MAX_REPLACEMENT_RATIO = float(os.getenv("QUALITY_MAX_REPLACEMENT_RATIO", "0.15"))
MIN_ALPHA_RATIO = float(os.getenv("QUALITY_MIN_ALPHA_RATIO", "0.50"))
MIN_CHAR_TO_SIZE_RATIO = float(os.getenv("QUALITY_MIN_CHAR_TO_SIZE_RATIO", "0.01"))


@dataclass
class QualityScore:
    """Quality assessment result"""
    score: float  # 0-1
    passed: bool  # True if score >= threshold
    needs_review: bool  # True if below threshold
    details: Dict  # Component scores
    extracted_chars: int
    pages: int
    method: str
    confidence: float
    threshold: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


def compute_quality_score(
    text: str,
    file_size: int,
    pages: int,
    method: str,
    extraction_confidence: float
) -> QualityScore:
    """
    Compute quality score for extracted text.
    
    Factors:
    1. Non-empty check
    2. Char count vs file size ratio
    3. Replacement character ratio (�)
    4. Alpha-numeric ratio
    5. Language sanity (common words)
    6. Extraction confidence
    """
    details = {}
    
    # 1. Non-empty
    if not text or not text.strip():
        return QualityScore(
            score=0.0,
            passed=False,
            needs_review=True,
            details={"error": "Empty text"},
            extracted_chars=0,
            pages=pages,
            method=method,
            confidence=extraction_confidence,
            threshold=QUALITY_THRESHOLD,
        )
    
    extracted_chars = len(text)
    details["extracted_chars"] = extracted_chars
    
    # 2. Char count vs file size ratio
    if file_size > 0:
        char_to_size_ratio = extracted_chars / file_size
        details["char_to_size_ratio"] = char_to_size_ratio
        size_score = min(1.0, char_to_size_ratio / MIN_CHAR_TO_SIZE_RATIO)
        details["size_score"] = size_score
    else:
        size_score = 1.0
        details["char_to_size_ratio"] = 0
        details["size_score"] = 1.0
    
    # 3. Replacement character ratio
    replacement_count = text.count('\ufffd')  # Unicode replacement char
    replacement_ratio = replacement_count / extracted_chars if extracted_chars > 0 else 0
    details["replacement_ratio"] = replacement_ratio
    replacement_score = max(0.0, 1.0 - (replacement_ratio / MAX_REPLACEMENT_RATIO))
    details["replacement_score"] = replacement_score
    
    # 4. Alpha-numeric ratio
    alpha_count = sum(1 for c in text if c.isalnum())
    alpha_ratio = alpha_count / extracted_chars if extracted_chars > 0 else 0
    details["alpha_ratio"] = alpha_ratio
    alpha_score = min(1.0, alpha_ratio / MIN_ALPHA_RATIO) if alpha_ratio > 0 else 0
    details["alpha_score"] = alpha_score
    
    # 5. Language sanity - check for common English words
    common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'a', 'an', 'the'}
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
    if words:
        common_count = sum(1 for w in words if w in common_words)
        language_ratio = common_count / len(words)
        details["language_ratio"] = language_ratio
        language_score = min(1.0, language_ratio * 3)  # Scale up
        details["language_score"] = language_score
    else:
        details["language_ratio"] = 0
        language_score = 0
        details["language_score"] = 0
    
    # 6. Extraction confidence (from extractor)
    details["extraction_confidence"] = extraction_confidence
    
    # Weighted combination
    weights = {
        "size_score": 0.0,
        "replacement_score": 0.25,
        "alpha_score": 0.25,
        "language_score": 0.40,
        "extraction_confidence": 0.10,
    }
    
    score = (
        weights["size_score"] * size_score +
        weights["replacement_score"] * replacement_score +
        weights["alpha_score"] * alpha_score +
        weights["language_score"] * language_score +
        weights["extraction_confidence"] * extraction_confidence
    )
    
    details["component_scores"] = {
        "size_score": size_score,
        "replacement_score": replacement_score,
        "alpha_score": alpha_score,
        "language_score": language_score,
        "extraction_confidence": extraction_confidence,
    }
    details["weights"] = weights
    details["final_score"] = score
    
    passed = score >= QUALITY_THRESHOLD
    needs_review = not passed
    
    return QualityScore(
        score=score,
        passed=passed,
        needs_review=needs_review,
        details=details,
        extracted_chars=extracted_chars,
        pages=pages,
        method=method,
        confidence=extraction_confidence,
        threshold=QUALITY_THRESHOLD,
    )


def assess_document_quality(
    db,
    document_id: str,
    extracted_text: str,
    file_size: int,
    pages: int,
    method: str,
    extraction_confidence: float
) -> QualityScore:
    """Assess and store quality for a document"""
    from app.models import Document
    
    score = compute_quality_score(
        text=extracted_text,
        file_size=file_size,
        pages=pages,
        method=method,
        extraction_confidence=extraction_confidence
    )
    
    # Update document status based on quality
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc:
        if score.needs_review:
            doc.status = 'needs_review' if hasattr(Document.status.type, 'enums') and 'needs_review' in Document.status.type.enums else doc.status
            # We'll add a quality_score column or use error_message for now
            doc.error_message = f"Quality score: {score.score:.2f} (threshold: {QUALITY_THRESHOLD})"
        db.commit()
    
    return score


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.quality <text_file> [file_size]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    file_size = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    score = compute_quality_score(text, file_size, 1, "test", 0.8)
    print(f"Score: {score.score:.3f}")
    print(f"Passed: {score.passed}")
    print(f"Needs review: {score.needs_review}")
    print(f"Details: {score.details}")