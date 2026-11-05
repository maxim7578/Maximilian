// NBT-AAD SSH-Werkzeug (Windows .exe)
// Verbindet sich per SSH mit der NBT-Evo-Headunit (über das ENET-Kabel) und erledigt die Schritte aus install.md:
// Verbindung testen, Log holen, Status, Installieren/Aktualisieren vom USB-Stick, dauerhaftes Log, iDrive neu
// starten. Bringt SSH selbst mit (x/crypto/ssh) und spricht die alten Algorithmen der Headunit, also kein
// Windows-SSH-Client nötig. Lesen (Log, Status) läuft ohne Rückfrage; verändernde Schritte fragen vorher.
//
// Build (Linux/macOS -> Windows): GOOS=windows GOARCH=amd64 go build -o nbt-aad-ssh.exe .
package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"golang.org/x/crypto/ssh"
	"golang.org/x/term"
)

const pluginDir = "/opt/hmi/ID5/data/ro/Plugins/NbtAad"

var pluginFiles = []string{"libNbtAad.so", "NbtAad.manifest", "NbtAad.xml", "NbtAad_ALL_Texts.zip", "NbtAad_ALL_Images.zip"}

var (
	headUnit = "169.254.199.99"
	port     = "22"
	stick    = ""
	in       = bufio.NewReader(os.Stdin)
)

func ask(prompt string) string {
	fmt.Print(prompt)
	s, _ := in.ReadString('\n')
	return strings.TrimSpace(s)
}

func confirm(what string) bool {
	a := strings.ToLower(ask(what + "  Wirklich ausführen? (j/n) "))
	return a == "j" || a == "ja"
}

// Legacy-tauglicher SSH-Client. Die Headunit ist alt: alte KEX, Chiffren, hmac-sha1 und ssh-rsa werden zusätzlich
// angeboten, damit die Aushandlung mit dem Server der Headunit klappt.
func connect(password string) (*ssh.Client, error) {
	cfg := &ssh.ClientConfig{
		User:            "root",
		Auth:            []ssh.AuthMethod{ssh.Password(password)},
		HostKeyCallback: ssh.InsecureIgnoreHostKey(), // Direktes Kabel, einmalige Verbindung: Host-Key nicht geprüft.
		HostKeyAlgorithms: []string{
			"rsa-sha2-256", "rsa-sha2-512", "ssh-rsa",
			"ecdsa-sha2-nistp256", "ssh-ed25519",
		},
		Timeout: 12 * time.Second,
	}
	cfg.KeyExchanges = []string{
		"curve25519-sha256", "curve25519-sha256@libssh.org",
		"ecdh-sha2-nistp256", "ecdh-sha2-nistp384", "ecdh-sha2-nistp521",
		"diffie-hellman-group14-sha256", "diffie-hellman-group14-sha1",
		"diffie-hellman-group-exchange-sha256", "diffie-hellman-group-exchange-sha1",
		"diffie-hellman-group1-sha1",
	}
	cfg.Ciphers = []string{
		"aes128-ctr", "aes192-ctr", "aes256-ctr",
		"aes128-gcm@openssh.com", "chacha20-poly1305@openssh.com",
		"aes128-cbc", "aes192-cbc", "aes256-cbc", "3des-cbc",
	}
	cfg.MACs = []string{"hmac-sha2-256", "hmac-sha2-512", "hmac-sha1", "hmac-sha1-96"}
	return ssh.Dial("tcp", headUnit+":"+port, cfg)
}

// Führt einen Befehl aus und gibt die Ausgabe (stdout+stderr) zurück.
func run(cli *ssh.Client, cmd string) (string, error) {
	s, err := cli.NewSession()
	if err != nil {
		return "", err
	}
	defer s.Close()
	out, err := s.CombinedOutput(cmd)
	return string(out), err
}

// Baut einen Befehl, der auf hu-omap läuft (dort liegen /opt, /mnt/umass..., /fs/sda0), wie "on -f /net/hu-omap/".
// Der innere Befehl darf kein einfaches Anführungszeichen enthalten.
func omap(inner string) string {
	return "on -f /net/hu-omap/ /bin/sh -c '" + inner + "'"
}

func printOut(out string) {
	for _, l := range strings.Split(strings.TrimRight(out, "\n"), "\n") {
		fmt.Println("  " + l)
	}
}

func findStick(cli *ssh.Client) string {
	if stick != "" {
		return stick
	}
	out, _ := run(cli, omap("ls /mnt/"))
	var found []string
	for _, l := range strings.Fields(out) {
		if strings.HasPrefix(l, "umass") {
			found = append(found, l)
		}
	}
	switch len(found) {
	case 1:
		stick = found[0]
		fmt.Println("USB-Stick: /mnt/" + stick)
	case 0:
		fmt.Println("Kein USB-Stick unter /mnt gefunden. Ausgabe:")
		printOut(out)
		stick = ask("Namen des Sticks eingeben (z. B. umass01200), leer = ohne: ")
	default:
		fmt.Println("Mehrere Sticks: " + strings.Join(found, ", "))
		stick = ask("Welchen nehmen: ")
	}
	return stick
}

func menuVerbindung(cli *ssh.Client) {
	fmt.Println("\n=== Verbindung testen ===")
	out, err := run(cli, omap("uname -a; echo; echo USB:; ls /mnt/"))
	if err != nil {
		fmt.Println("Fehler: " + err.Error())
	}
	printOut(out)
}

func menuLog(cli *ssh.Client) {
	fmt.Println("\n=== Log holen ===")
	s := findStick(cli)
	var srcs []string
	if s != "" {
		srcs = append(srcs, "/mnt/"+s+"/nbt-aad.log", "/mnt/"+s+"/nbt-aad-app.log")
	}
	srcs = append(srcs, "/dev/shmem/nbt-aad.log", "/dev/shmem/nbt-aad-app.log")
	inner := ""
	for _, q := range srcs {
		inner += "if [ -f " + q + " ]; then echo; echo ===== " + q + " =====; tail -n 3000 " + q + "; fi; "
	}
	inner += "echo; echo ===== Status =====; ls -l /opt/aa/ " + pluginDir + "/ 2>&1; cat /dev/shmem/nbt-aad-state 2>&1"
	out, _ := run(cli, omap(inner))
	name := "nbt-aad-log_" + time.Now().Format("2006-01-02_15-04-05") + ".txt"
	path := onDesktop(name)
	if err := os.WriteFile(path, []byte(out), 0600); err != nil {
		path = name
		_ = os.WriteFile(path, []byte(out), 0600)
	}
	fmt.Println("Gespeichert: " + path)
	fmt.Println("Diese Datei kannst du Claude anhängen.")
	fmt.Println("\nWichtigste Zeilen:")
	for _, l := range strings.Split(out, "\n") {
		if containsAny(l, "Wireless]", "TcpServer", "BluetoothManager", "[PF]", "[Mic]", "ERROR", "FAILED", "refus", "session ended", "connected over") {
			fmt.Println("  " + l)
		}
	}
}

func menuStatus(cli *ssh.Client) {
	fmt.Println("\n=== Status ===")
	out, _ := run(cli, omap("echo Daemon:; ls -l /opt/aa/ 2>&1; echo; echo Plugin:; ls -l "+pluginDir+"/ 2>&1; echo; echo Zustand:; cat /dev/shmem/nbt-aad-state 2>&1; echo; echo Einstellungen:; cat /opt/aa/nbt-aad.env 2>&1"))
	printOut(out)
}

func setBeschreibbar(cli *ssh.Client) {
	fmt.Println("Systempartition beschreibbar machen ...")
	out, _ := run(cli, "mount -o remount rw /net/hu-omap/fs/sda0")
	if strings.TrimSpace(out) != "" {
		printOut(out)
	}
}

func menuInstallieren(cli *ssh.Client) {
	fmt.Println("\n=== Installieren / Aktualisieren vom USB-Stick ===")
	s := findStick(cli)
	if s == "" {
		fmt.Println("Ohne Stick geht das nicht.")
		return
	}
	m := "/mnt/" + s
	check := "ls -l " + m + "/nbt-aad"
	for _, f := range pluginFiles {
		check += " " + m + "/release/" + f
	}
	out, err := run(cli, omap(check))
	printOut(out)
	if err != nil {
		fmt.Println("Auf dem Stick fehlt etwas (siehe oben). Abbruch, nichts verändert.")
		return
	}
	if !confirm("Kopiert nbt-aad nach /opt/aa und die iDrive-App nach " + pluginDir + " (alte Dateien werden als .old aufgehoben).") {
		return
	}
	setBeschreibbar(cli)
	cmd := "mkdir -p /fs/sda0/opt/aa && " +
		"if [ -f /opt/aa/nbt-aad ]; then mv /opt/aa/nbt-aad /opt/aa/nbt-aad.old; fi && " +
		"cp " + m + "/nbt-aad /opt/aa/nbt-aad && chmod 755 /opt/aa/nbt-aad && " +
		"mkdir -p " + pluginDir + " && " +
		"if [ -f " + pluginDir + "/libNbtAad.so ]; then mv " + pluginDir + "/libNbtAad.so " + pluginDir + "/libNbtAad.so.old; fi"
	for _, f := range pluginFiles {
		cmd += " && cp " + m + "/release/" + f + " " + pluginDir + "/" + f
	}
	cmd += " && sync && echo && echo KURZTEST: && /opt/aa/nbt-aad --license | head -3 && echo && ls -l /opt/aa/ " + pluginDir + "/"
	out, err = run(cli, omap(cmd))
	printOut(out)
	if err == nil {
		fmt.Println("Installiert. Danach iDrive neu starten (Menüpunkt 6).")
	} else {
		fmt.Println("Fehler beim Installieren. Bitte die Ausgabe oben an Claude schicken.")
	}
}

func menuDauerLog(cli *ssh.Client) {
	fmt.Println("\n=== Dauerhaftes Log auf dem USB-Stick ===")
	s := findStick(cli)
	if s == "" {
		fmt.Println("Ohne Stick geht das nicht.")
		return
	}
	fmt.Println("Schreibt NBT_LOG_FILE=/mnt/" + s + "/nbt-aad.log in /opt/aa/nbt-aad.env.")
	if !confirm("Einstellungsdatei schreiben.") {
		return
	}
	setBeschreibbar(cli)
	cmd := "touch /opt/aa/nbt-aad.env && grep -v ^NBT_LOG_FILE= /opt/aa/nbt-aad.env > /dev/shmem/nbt-aad.env.neu; " +
		"echo NBT_LOG_FILE=/mnt/" + s + "/nbt-aad.log >> /dev/shmem/nbt-aad.env.neu && " +
		"cp /dev/shmem/nbt-aad.env.neu /opt/aa/nbt-aad.env && rm /dev/shmem/nbt-aad.env.neu && sync && cat /opt/aa/nbt-aad.env"
	out, _ := run(cli, omap(cmd))
	printOut(out)
	fmt.Println("Gilt ab dem nächsten Start von Android Auto.")
}

func menuNeustart(cli *ssh.Client) {
	fmt.Println("\n=== iDrive neu starten ===")
	if !confirm("Der Bildschirm geht kurz aus, die Verbindung kann abbrechen.") {
		return
	}
	_, _ = run(cli, omap("sync; OnOffDSICommander appreset"))
	fmt.Println("Befehl gesendet. Falls kein Menüpunkt erscheint: Ein-/Aus-Knopf der Headunit ca. 30 s halten.")
}

func containsAny(s string, subs ...string) bool {
	for _, sub := range subs {
		if strings.Contains(s, sub) {
			return true
		}
	}
	return false
}

func onDesktop(name string) string {
	home, err := os.UserHomeDir()
	if err != nil {
		return name
	}
	d := filepath.Join(home, "Desktop")
	if _, err := os.Stat(d); err == nil {
		return filepath.Join(d, name)
	}
	return filepath.Join(home, name)
}

func parseArgs() {
	for i := 1; i < len(os.Args); i++ {
		switch os.Args[i] {
		case "-host", "--host":
			if i+1 < len(os.Args) {
				i++
				headUnit = os.Args[i]
			}
		case "-port", "--port":
			if i+1 < len(os.Args) {
				i++
				port = os.Args[i]
			}
		}
	}
}

func readPassword() string {
	fmt.Print("Passwort der Headunit: ")
	b, err := term.ReadPassword(int(os.Stdin.Fd()))
	fmt.Println()
	if err != nil { // kein echtes Terminal: normal einlesen
		return ask("")
	}
	return strings.TrimSpace(string(b))
}

func main() {
	parseArgs()
	fmt.Println("NBT-AAD SSH-Werkzeug  -  Headunit " + headUnit + ", Port " + port)
	if a := ask("Andere Adresse? Enter = " + headUnit + ", sonst IP eingeben: "); a != "" {
		headUnit = a
	}
	// Über den TurboCode-ENET-Proxy ist die Headunit meist 127.0.0.1 auf Port 6969 statt 22.
	if a := ask("Port? Enter = " + port + " (TurboCode-Proxy: 6969): "); a != "" {
		port = a
	}
	pw := readPassword()
	fmt.Println("Verbinde ...")
	cli, err := connect(pw)
	if err != nil {
		fmt.Println("Verbindung fehlgeschlagen: " + err.Error())
		fmt.Println("Prüfe ENET-Kabel, Zündung an, und die Netzwerkadresse des Laptops (169.254.x.x).")
		ask("Enter zum Beenden ")
		return
	}
	defer cli.Close()
	fmt.Println("Verbunden.")
	for {
		fmt.Println("\n1  Verbindung testen")
		fmt.Println("2  Log holen (Datei auf dem Desktop)")
		fmt.Println("3  Status anzeigen")
		fmt.Println("4  Installieren / Aktualisieren vom USB-Stick")
		fmt.Println("5  Dauerhaftes Log auf dem USB-Stick einschalten")
		fmt.Println("6  iDrive neu starten")
		fmt.Println("0  Beenden")
		switch ask("Auswahl: ") {
		case "1":
			menuVerbindung(cli)
		case "2":
			menuLog(cli)
		case "3":
			menuStatus(cli)
		case "4":
			menuInstallieren(cli)
		case "5":
			menuDauerLog(cli)
		case "6":
			menuNeustart(cli)
		case "0":
			return
		default:
			fmt.Println("Bitte 0 bis 6 eingeben.")
		}
	}
}
