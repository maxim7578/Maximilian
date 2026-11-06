package com.bmwhuinfo

import com.bmwhuinfo.data.Safety
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Tests der Sicherheitsschicht: nur Lesebefehle duerfen durch. */
class SafetyTest {

    @Test
    fun `laesst einfachen Lesebefehl durch`() {
        assertTrue(Safety.istLesebefehl("uname -a"))
    }

    @Test
    fun `laesst Pipe mit grep durch`() {
        assertTrue(Safety.istLesebefehl("dmesg | grep -i error"))
    }

    @Test
    fun `Pipe in Anfuehrungszeichen ist kein Trenner`() {
        assertTrue(Safety.istLesebefehl("dmesg | grep -i -E 'error|fail|warn'"))
    }

    @Test
    fun `verweigert unbalancierte Anfuehrungszeichen`() {
        assertFalse(Safety.istLesebefehl("grep 'offen"))
    }

    @Test
    fun `verweigert rm`() {
        assertFalse(Safety.istLesebefehl("rm -rf /"))
    }

    @Test
    fun `verweigert Umleitung`() {
        assertFalse(Safety.istLesebefehl("echo kaputt > /etc/wichtig"))
    }

    @Test
    fun `verweigert Befehlskettung`() {
        assertFalse(Safety.istLesebefehl("uname -a; rm -rf /"))
    }

    @Test
    fun `verweigert sed in place`() {
        assertFalse(Safety.istLesebefehl("sed -i s/a/b/ datei"))
    }

    @Test
    fun `verweigert find exec`() {
        assertFalse(Safety.istLesebefehl("find / -name x -exec rm {} ;"))
    }

    @Test
    fun `verweigert Platzhalter`() {
        assertFalse(Safety.istLesebefehl("cat <PFAD_ZUR_VIN_DATEI>"))
    }

    @Test
    fun `verweigert unbekanntes Programm`() {
        assertFalse(Safety.istLesebefehl("flash_tool --write"))
    }
}
