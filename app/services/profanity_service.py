import re
import unicodedata

# Prohibited root words and patterns
PROFANITY_PATTERNS = [
    # Uzbek bad words / insults
    r"jalab", r"zhalab", r"harom[iy]?", r"xarom[iy]?", r"q[o']?t[ao]q", r"qotag",
    r"sik[a-z]*", r"skaman", r"skay", r"am[iy]?[zs]?", r"amcha", r"itvachch?a",
    r"onang[a-z]*", r"enag[a-z]*", r"padar[a-z]*", r"gandon", r"dalba[ye]?[eo]b",
    r"musr", r"musor", r"fohisha", r"buzuq[a-z]*", r"k[o']?t[td]?[a-z]*", r"chala[a-z]*",
    r"mol[a-z]*", r"eshak[a-z]*", r"ahmoq", r"tupoy", r"lox", r"chmo", r"krisa",
    r"hezzalak", r"xunasa", r"ge[iy]", r"trans",
    
    # Russian profanity / mat
    r"blya[td]?[a-z]*", r"bl[eya]d", r"suka", r"suchka", r"xuy[a-z]*", r"huy[a-z]*",
    r"pizd[a-z]*", r"[ye]ba[lt][a-z]*", r"za[ye]b[a-z]*", r"prostitutka",
    r"mudak[a-z]*", r"shlyux[a-z]*", r"pidor[a-z]*", r"pedik", r"eblan",
    r"droch[a-z]*", r"chlen", r"gnida", r"tvar",
    
    # English profanity
    r"fuck[a-z]*", r"fck", r"shit[a-z]*", r"bitch[a-z]*", r"cunt[a-z]*",
    r"asshole", r"dick[a-z]*", r"pussy[a-z]*", r"whore", r"slut",
    r"nigg[ae]r?", r"retard", r"bastard"
]

# Character normalization map (leetspeak & lookalikes)
LEET_MAP = {
    '@': 'a', '4': 'a', '0': 'o', '1': 'i', '!': 'i', '|': 'i',
    '3': 'e', '5': 's', '$': 's', '7': 't', '8': 'b',
    'ҳ': 'h', 'х': 'x', 'а': 'a', 'в': 'v', 'е': 'e', 'к': 'k',
    'м': 'm', 'н': 'n', 'о': 'o', 'р': 'r', 'с': 's', 'т': 't',
    'у': 'u', 'я': 'ya', 'ё': 'yo', 'ю': 'yu', 'ш': 'sh', 'ч': 'ch'
}

COMPILED_PATTERNS = [re.compile(rf"\b{p}\b", re.IGNORECASE) for p in PROFANITY_PATTERNS] + [
    re.compile(p, re.IGNORECASE) for p in [
        r"jalab", r"qotoq", r"qo'toq", r"sikish", r"sikaman", r"sikyap", r"blyad", r"pizda", r"xuy", r"huy",
        r"gandon", r"dalbayob", r"fuck", r"bitch", r"nigger", r"mudak", r"pidor"
    ]
]


class ProfanityService:
    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        text = text.lower()
        # Unicode normalization
        text = unicodedata.normalize('NFKD', text)
        # Apply leetspeak replacement
        chars = []
        for ch in text:
            chars.append(LEET_MAP.get(ch, ch))
        norm = "".join(chars)
        # Remove repeated excessive characters e.g. "ssssiiikkk" -> "sik"
        norm = re.sub(r'(.)\1{2,}', r'\1\1', norm)
        return norm

    @classmethod
    def contains_profanity(cls, text: str) -> bool:
        if not text:
            return False
        normalized = cls.normalize_text(text)
        
        # 1. Direct word match
        words = re.findall(r'[a-z0-9\']+', normalized)
        for w in words:
            for pattern in COMPILED_PATTERNS:
                if pattern.search(w):
                    return True

        # 2. Check full string with whitespace stripped (e.g. "s i k i s h")
        stripped = re.sub(r'[^a-z0-9\']', '', normalized)
        for pattern in COMPILED_PATTERNS:
            if pattern.search(stripped):
                return True

        # 3. Direct pattern search on full text
        for pattern in COMPILED_PATTERNS:
            if pattern.search(normalized):
                return True

        return False
