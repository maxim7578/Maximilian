package com.bmwhuinfo.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.bmwhuinfo.data.Befehl

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DiagnoseScreen(viewModel: DiagnoseViewModel) {
    val zustand by viewModel.zustand.collectAsStateWithLifecycle()
    val katalog = viewModel.katalog

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("BMW HU Info - Diagnose (nur Lesen)")

        OutlinedTextField(
            value = zustand.host,
            onValueChange = viewModel::setHost,
            label = { Text("IP der Headunit") },
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = zustand.port,
                onValueChange = viewModel::setPort,
                label = { Text("Port") },
                modifier = Modifier.weight(1f),
            )
            OutlinedTextField(
                value = zustand.benutzer,
                onValueChange = viewModel::setBenutzer,
                label = { Text("Benutzer") },
                modifier = Modifier.weight(2f),
            )
        }
        OutlinedTextField(
            value = zustand.passwort,
            onValueChange = viewModel::setPasswort,
            label = { Text("Passwort (oder leer bei Schluessel)") },
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = zustand.privaterSchluessel,
            onValueChange = viewModel::setSchluessel,
            label = { Text("Privater Schluessel (PEM, optional)") },
            modifier = Modifier.fillMaxWidth(),
        )

        Text("Headunit:")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            DiagnoseZustand.HEADUNITS.forEach { hu ->
                FilterChip(
                    selected = zustand.headunit == hu,
                    onClick = { viewModel.setHeadunit(hu) },
                    label = { Text(hu) },
                )
            }
        }

        val alleBefehle = katalog.kategorien.flatMap { it.befehle }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = { viewModel.fuehreAus(alleBefehle) },
                enabled = !zustand.laeuft,
            ) { Text("Alle lesen") }
            OutlinedButton(
                onClick = { viewModel.ausgabeLeeren() },
                enabled = !zustand.laeuft,
            ) { Text("Ausgabe leeren") }
            if (zustand.laeuft) {
                CircularProgressIndicator(modifier = Modifier.padding(start = 8.dp))
            }
        }

        Divider()
        katalog.kategorien.forEach { kategorie ->
            Text("-- ${kategorie.titel} --")
            kategorie.befehle.forEach { befehl ->
                BefehlZeile(befehl) { viewModel.fuehreAus(listOf(befehl)) }
            }
        }

        if (zustand.ausgabe.isNotEmpty()) {
            Divider()
            Text("Ausgabe:")
            Text(text = zustand.ausgabe, fontFamily = FontFamily.Monospace)
        }
    }
}

@Composable
private fun BefehlZeile(befehl: Befehl, onKlick: () -> Unit) {
    val beschriftung = if (befehl.hatPlatzhalter) "${befehl.titel} [Platzhalter]" else befehl.titel
    OutlinedButton(
        onClick = onKlick,
        enabled = !befehl.hatPlatzhalter,
        modifier = Modifier.fillMaxWidth(),
    ) { Text(beschriftung) }
}
