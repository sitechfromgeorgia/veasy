"""Word timings for a voice track we know the text of (forced alignment), for engines that don't
return them (Gemini TTS). Georgian uses a wav2vec2 CTC model with a Georgian character vocabulary.

Runs in the torch venv as its own process, so the render venv stays light:
  python -m tt_shorts.align <audio> <text file> <words.json> [lang]
Words with no letters the model knows ("AI", "83%") get times interpolated from their neighbours.
The same model also transcribes the track (greedy CTC) into <words>.heard.txt: render.voice_qa() compares
it with the text the voice was given, to flag words the voice skipped or said differently ($0, no extra model).
"""
import json
import sys

MODELS = {"ka": "xsway/wav2vec2-large-xlsr-georgian"}  # Apache-2.0; the WhisperX alignment default for ka


def align(audio, text, lang="ka"):
    import torch
    import torchaudio
    from torchaudio.functional import forced_align, merge_tokens
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

    name = MODELS[lang]
    proc = Wav2Vec2Processor.from_pretrained(name)
    model = Wav2Vec2ForCTC.from_pretrained(name).eval()
    vocab = proc.tokenizer.get_vocab()
    blank, sep = proc.tokenizer.pad_token_id, vocab.get("|")

    wav, sr = torchaudio.load(audio)
    wav = torchaudio.functional.resample(wav.mean(0), sr, 16000)
    with torch.inference_mode():
        inputs = proc(wav.numpy(), sampling_rate=16000, return_tensors="pt").input_values
        emission = torch.log_softmax(model(inputs).logits, dim=-1)
    sec_per_frame = wav.shape[0] / 16000 / emission.shape[1]
    align.heard = proc.batch_decode(emission.argmax(-1))[0]  # what the model hears, for the voice check

    words = text.split()
    targets, owner = [], []
    for i, w in enumerate(words):
        ids = [vocab[c] for c in w.lower() if c in vocab and vocab[c] not in (blank, sep)]
        if not ids:
            continue
        if targets and sep is not None:
            targets.append(sep)
            owner.append(-1)
        targets += ids
        owner += [i] * len(ids)
    if not targets:
        raise ValueError("nothing to align: no word has letters the model knows")
    path, scores = forced_align(emission, torch.tensor([targets], dtype=torch.int32), blank=blank)
    spans = merge_tokens(path[0], scores[0].exp(), blank=blank)  # its default blank=0 isn't this model's
    if len(spans) != len(targets):
        raise RuntimeError(f"alignment mismatch: {len(spans)} spans for {len(targets)} tokens")

    times = {}
    for span, i in zip(spans, owner):
        if i < 0:
            continue
        s, e = span.start * sec_per_frame, span.end * sec_per_frame
        a, b = times.get(i, (s, e))
        times[i] = (min(a, s), max(b, e))
    out, total = [], wav.shape[0] / 16000
    for i, w in enumerate(words):
        if i in times:
            s, e = times[i]
            if any(c.isalnum() and c.lower() not in vocab for c in w):  # "Microsoft-ის": only "ის" was heard
                s = out[-1]["end"] if out else 0.0
        else:  # no known letters: share the gap between the neighbours
            prev = max((times[j][1] for j in times if j < i), default=0.0)
            nxt = min((times[j][0] for j in times if j > i), default=total)
            s, e = prev, max(prev + 0.05, nxt)
        out.append({"text": w, "start": round(s, 3), "end": round(e, 3)})
    return out


if __name__ == "__main__":
    audio, text_file, out_file = sys.argv[1:4]
    lang = sys.argv[4] if len(sys.argv) > 4 else "ka"
    words = align(audio, open(text_file, encoding="utf-8").read(), lang)
    open(out_file, "w", encoding="utf-8").write(json.dumps(words, ensure_ascii=False, indent=1))
    open(out_file.rsplit(".", 1)[0] + ".heard.txt", "w", encoding="utf-8").write(getattr(align, "heard", ""))
    print(f"aligned {len(words)} words")
