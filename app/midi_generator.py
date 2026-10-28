import pretty_midi

def melody_to_midi(melody, path):
    pm = pretty_midi.PrettyMIDI()
    inst = pretty_midi.Instrument(program=0)  # piano
    for n in melody["notes"]:
        note = pretty_midi.Note(velocity=100, pitch=n["midi_note"], start=n["start"], end=n["start"]+n["duration"])
        inst.notes.append(note)
    pm.instruments.append(inst)
    pm.write(path)
    return path
