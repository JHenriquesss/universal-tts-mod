from install_tts_mod import install_game


def choose_game_folder(askdirectory=None):
    if askdirectory is None:
        from tkinter import Tk, filedialog

        root = Tk()
        root.withdraw()
        try:
            return filedialog.askdirectory(title="Selecione a pasta do jogo (Ren'Py ou Unity)")
        finally:
            root.destroy()
    return askdirectory(title="Selecione a pasta do jogo (Ren'Py ou Unity)")


def install_selected_game(game_folder=None, askdirectory=None, showinfo=None, showerror=None):
    if game_folder is None:
        game_folder = choose_game_folder(askdirectory=askdirectory)
    if not game_folder:
        return None

    try:
        result = install_game(game_folder)
    except Exception as exc:
        if showerror is None:
            from tkinter import messagebox

            showerror = messagebox.showerror
        showerror("Falha na Instalação do Mod TTS", str(exc))
        raise

    message = f"[{result.engine.upper()}] Mod TTS instalado com sucesso!\n\n{len(result.installed)} arquivos copiados para:\n{result.game_root}"
    if showinfo is None:
        from tkinter import messagebox

        showinfo = messagebox.showinfo
    showinfo("Instalação Concluída", message)
    return result


def main():
    install_selected_game()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
