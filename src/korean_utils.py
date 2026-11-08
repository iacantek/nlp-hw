"""Korean morphosyntactic particle resolution and script/language analysis utilities.

Provides deterministic handling of Korean postpositional particle alternations
(e.g., 은/는, 이/가, 을/를, 과/와, 으로/로) conditioned on whether the preceding
noun or numeral ends in a final consonant (batchim / 받침), as well as script
detection utilities for measuring output language consistency and language drift.
"""

from __future__ import annotations

import re

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3
JONGSEONG_RIEUL = 8

# Sino-Korean readings of final digits:
# 0 (영/공: ㅇ batchim), 1 (일: ㄹ batchim), 2 (이: vowel), 3 (삼: ㅁ batchim),
# 4 (사: vowel), 5 (오: vowel), 6 (육: ㄱ batchim), 7 (칠: ㄹ batchim),
# 8 (팔: ㄹ batchim), 9 (구: vowel)
DIGIT_BATCHIM: dict[str, tuple[bool, bool]] = {
    "0": (True, False),
    "1": (True, True),
    "2": (False, False),
    "3": (True, False),
    "4": (False, False),
    "5": (False, False),
    "6": (True, False),
    "7": (True, True),
    "8": (True, True),
    "9": (False, False),
}

# Basic Latin letter-name approximations if a Latin token precedes a Korean particle
LATIN_VOWEL_ENDINGS = set("aeiouyAEIOUY")
LATIN_RIEUL_ENDINGS = set("lL")

PARTICLE_MAP: dict[str, tuple[str, str]] = {
    "은/는": ("은", "는"),
    "이/가": ("이", "가"),
    "을/를": ("을", "를"),
    "과/와": ("과", "와"),
    "으로/로": ("으로", "로"),
    "이다/다": ("이다", "다"),
    "이라고/라고": ("이라고", "라고"),
}

_STRIP_TRAILING_RE = re.compile(r"[\s\"'`’”)\]}>.,!?;:]+$")
_PARTICLE_PATTERN = re.compile(
    r"\{(" + "|".join(re.escape(k) for k in PARTICLE_MAP) + r")\}"
)


def get_batchim_info(word: str) -> tuple[bool, bool]:
    """Return (has_batchim, is_rieul) for the final pronounced character of `word`.

    Args:
        word: The surface string preceding a Korean particle.

    Returns:
        A tuple `(has_batchim, is_rieul)` where `has_batchim` is True if the final
        syllable has a coda consonant (받침) and `is_rieul` is True if that coda is ㄹ.
    """
    cleaned = _STRIP_TRAILING_RE.sub("", word.strip())
    if not cleaned:
        return (False, False)

    last_char = cleaned[-1]
    code = ord(last_char)

    # 1. Standard Hangul syllable block (가-힣)
    if HANGUL_START <= code <= HANGUL_END:
        jongseong = (code - HANGUL_START) % 28
        return (jongseong != 0, jongseong == JONGSEONG_RIEUL)

    # 2. Arabic numerals
    if last_char.isdigit():
        # Multi-digit round numbers ending in 0 (10 십, 100 백, 1000 천, 10000 만)
        # all end in a non-rieul consonant in Sino-Korean.
        return DIGIT_BATCHIM[last_char]

    # 3. Fallback for Latin characters
    if last_char.isalpha():
        if last_char in LATIN_VOWEL_ENDINGS:
            return (False, False)
        if last_char in LATIN_RIEUL_ENDINGS:
            return (True, True)
        return (True, False)

    return (False, False)


def select_particle(word: str, particle_spec: str) -> str:
    """Select the grammatically appropriate Korean particle for `word`.

    Args:
        word: Preceding noun or entity string.
        particle_spec: One of '은/는', '이/가', '을/를', '과/와', '으로/로',
            '이다/다', '이라고/라고'.

    Returns:
        The selected particle string.
    """
    if particle_spec not in PARTICLE_MAP:
        raise ValueError(f"Unsupported particle specification: {particle_spec!r}")

    has_batchim, is_rieul = get_batchim_info(word)
    with_batchim, without_batchim = PARTICLE_MAP[particle_spec]

    if particle_spec == "으로/로":
        # '로' is used after vowels AND after 'ㄹ' (rieul) batchim
        if not has_batchim or is_rieul:
            return without_batchim
        return with_batchim

    return with_batchim if has_batchim else without_batchim


def resolve_korean_particles(text: str) -> str:
    """Resolve all `{은/는}`, `{이/가}`, `{을/를}`, `{과/와}`, `{으로/로}` markers in `text`.

    Looks at the substring immediately preceding each `{...}` marker to select
    the appropriate morphosyntactic variant.
    """
    result: list[str] = []
    last_idx = 0
    for match in _PARTICLE_PATTERN.finditer(text):
        prefix = text[last_idx : match.start()]
        result.append(prefix)
        preceding_context = "".join(result)
        particle_spec = match.group(1)
        chosen = select_particle(preceding_context, particle_spec)
        result.append(chosen)
        last_idx = match.end()
    result.append(text[last_idx:])
    return "".join(result)


def count_hangul_chars(text: str) -> int:
    """Count Hangul syllables and compatibility jamo in `text`."""
    return sum(
        1
        for ch in text
        if (HANGUL_START <= ord(ch) <= HANGUL_END) or (0x3130 <= ord(ch) <= 0x318F)
    )


def count_latin_chars(text: str) -> int:
    """Count ASCII Latin alphabetic characters in `text`."""
    return sum(1 for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))


def detect_output_language(text: str, query_lang: str = "en") -> str:
    """Classify surface script/language of a generated response.

    Returns:
        - 'ko' if Hangul characters dominate,
        - 'en' if Latin characters dominate,
        - 'neutral' if the output consists solely of shared numerals/symbols
          (e.g., '1935' or '8'), which is language-consistent with both 'en' and 'ko'.
    """
    n_ko = count_hangul_chars(text)
    n_en = count_latin_chars(text)
    if n_ko == 0 and n_en == 0:
        return "neutral"
    if n_ko > 0 and n_en == 0:
        return "ko"
    if n_en > 0 and n_ko == 0:
        return "en"
    # Mixed output: classify by dominant script character count
    return "ko" if n_ko >= n_en else "en"


def is_language_consistent(text: str, target_lang: str) -> bool:
    """Return True if `text` is consistent with `target_lang` ('en' or 'ko').

    Purely numeric responses ('neutral') are treated as consistent with both
    English and Korean queries (following Li et al., 2025).
    """
    detected = detect_output_language(text, query_lang=target_lang)
    return detected in (target_lang, "neutral")
