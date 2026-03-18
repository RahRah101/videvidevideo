import re

#expand the whole script
#script is expected to be a dict
#TODO: Use Pydantic to validate and/or add errors 
def expand(script):
    meta = expand_meta(script.get('meta', {}))
    entries = script.get("s", [])
    expanded_entries = []

    for entry in entries:
        expanded_entries.extend(expand_entry(entry))

    return

#expand the metadata 
def expand_meta(meta):
    return {
        "title": meta.get("title")
        "voice_id": meta.get("voice", ""),
        "char_lim": meta.get("char_lim", 5000),
        "fps": meta.get("fps", 30),
        "resolution": meta.get("res", [1920, 1080]),
        "assets_dir": meta.get("assets_dir", "assets/"),
    }


def expand_entry(entry):
    results = []

    # --- narrate ---
    if "n" in entry:
        narration = {"narrate": str(entry["n"])}

        # check for @word: cues
        #TODO: Fuck that shit for now, to implement in the 2nd stage
        """ Ugly ass triple quote
        for key in entry:
            if key.startswith("@"):
                word = key[1:]
                value = entry[key]
                narration["on_word"] = word

                if isinstance(value, str) and re.match(r"^\{(.+)\}$", value.strip()):
                    narration["effect"] = re.match(r"^\{(.+)\}$", value.strip()).group(1)
                else:
                    narration["edit"] = value
        """
        results.append(narration)
    
    #video clip
    if "v" in entry:
        results.append(parse_clip(entry["v"]))

    #image
    if "i" in entry:
        results.append(parse_image(entry["i"]))

    #pause
    if "_" in entry:
        results.append({"pause": float(entry["_"])})

    #text overlay
    if "t" in entry:
        results.append(parse_text_overlay(entry["t"]))

    #edit (natural language)
    if "e" in entry:
        edit = {"edit": entry["e"]}

        if "+" in entry:
            edit["media"] = entry["+"]
            # parse timestamps from media string if present
            if isinstance(edit["media"], str):
                ts = re.search(r"\s+(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$", edit["media"])
                if ts:
                    edit["from"] = parse_timestamp(ts.group(1))
                    edit["to"] = parse_timestamp(ts.group(2))
                    edit["media"] = edit["media"][:ts.start()].strip()

        if "d" in entry:
            edit["duration"] = float(entry["d"])

        results.append(edit)
    return results

def parse_timestamp(ts):
    """Convert dot notation to seconds. '1.05' -> 65, '12' -> 12, '0.30' -> 30"""
    ts = str(ts).strip()
    if "." in ts:
        parts = ts.split(".")
        return int(parts[0]) * 60 + int(parts[1])
    return int(ts)


def parse_clip(value):
    value = str(value)
    clip = {}

    # extract timestamp range e.g. "sample.mp4 1.05-1.12"
    # match a timestamp pair at the end: digits/dots, dash, digits/dots
    ts = re.search(r"\s+(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$", value)
    if ts:
        clip["from"] = parse_timestamp(ts.group(1))
        clip["to"] = parse_timestamp(ts.group(2))
        value = value[:ts.start()].strip()

    clip["clip"] = value
    return clip


def parse_image(value):
    value = str(value)
    image = {}

    # extract {effect}
    effect = re.search(r"\{(.+?)\}", value)
    if effect:
        image["transition"] = effect.group(1)
        value = re.sub(r"\s*\{.+?\}", "", value).strip()

    # check for -> transition
    if "->" in value:
        parts = [p.strip() for p in value.split("->")]
        image["image"] = parts[0]
        image["to"] = parts[1]
    else:
        image["image"] = value.strip()

    return image


def parse_text_overlay(value):
    value = str(value)
    overlay = {}

    # extract {style}
    style = re.search(r"\{(.+?)\}", value)
    if style:
        overlay["style"] = style.group(1)
        value = re.sub(r"\s*\{.+?\}", "", value).strip()

    # extract duration (e.g. "3s")
    dur = re.search(r"(\d+(?:\.\d+)?)\s*s\b", value)
    if dur:
        overlay["duration"] = float(dur.group(1))
        value = re.sub(r"\s*\d+(?:\.\d+)?\s*s\b", "", value).strip()

    # remaining text — strip quotes if present
    text = value.strip().strip('"').strip("'")
    overlay["text_overlay"] = text

    return overlay
