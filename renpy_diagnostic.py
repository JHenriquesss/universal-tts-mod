import pickle
import sys

def analyze_renpy_save(file_path):
    try:
        with open(file_path, "rb") as f:
            # Ren'Py saves usually start with a header, then a pickle.
            # We skip the header (it contains things like the Ren'Py version).
            data = f.read()
            
            # Find the start of the pickle stream (it's often preceded by a marker)
            # In modern Ren'Py, the save is a tuple of (save_name, thumbnail, log)
            # and it's often zlib compressed or just a pickle.
            # Let's try to find the start of a pickle object.
            # However, simpler: just try to find route strings in the binary data.
            
            interesting_vars = [
                b"route_siren", b"route_kitten", b"route_cuck",
                b"route_fiona", b"route_kate", b"route_evelyn",
                b"route_natasha", b"route_lexi", b"route_delilah",
                b"route_rachel", b"persistent"
            ]
            
            print(f"--- Analisando arquivo: {file_path} ---")
            
            # Brute force search for route variables in the binary
            for var in interesting_vars:
                idx = data.find(var)
                if idx != -1:
                    print(f"\nEncontrado: {var.decode()}")
                    # Print context around the find to see boolean flags or strings
                    context = data[idx:idx+100]
                    # Represent binary in a readable hex-ish way for diagnostic
                    readable = "".join([chr(b) if 32 <= b <= 126 else "." for b in context])
                    print(f"Contexto: {readable}")
                    
                    if b"\x88" in context or b"I01" in context:
                        print(f"Status {var.decode()}: ATIVO (True)")
                    elif b"\x89" in context or b"I00" in context:
                        print(f"Status {var.decode()}: INATIVO (False)")
                    else:
                        print(f"Status {var.decode()}: Indeterminado (ver contexto)")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    analyze_renpy_save(sys.argv[1])
