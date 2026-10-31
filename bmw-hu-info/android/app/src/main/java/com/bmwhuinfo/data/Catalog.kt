package com.bmwhuinfo.data

import android.content.Context
import org.json.JSONObject

/** Ein einzelner Diagnosebefehl. */
data class Befehl(
    val id: String,
    val titel: String,
    val command: String,
    val headunits: List<String>,
    val hinweis: String = "",
) {
    val hatPlatzhalter: Boolean
        get() = command.contains("<") && command.contains(">")
}

/** Eine Gruppe von Befehlen. */
data class Kategorie(
    val id: String,
    val titel: String,
    val befehle: List<Befehl>,
)

/** Der gesamte Befehlskatalog. */
data class Katalog(
    val version: Int,
    val beschreibung: String,
    val kategorien: List<Kategorie>,
) {
    /** Neuer, auf eine Headunit gefilterter Katalog (immutabel). */
    fun fuerHeadunit(headunit: String): Katalog {
        val gefiltert = kategorien
            .map { kat -> kat.copy(befehle = kat.befehle.filter { headunit in it.headunits }) }
            .filter { it.befehle.isNotEmpty() }
        return copy(kategorien = gefiltert)
    }

    companion object {
        /** Laedt den Katalog aus den App-Assets (commands.json). */
        fun ausAssets(context: Context, dateiname: String = "commands.json"): Katalog {
            val text = context.assets.open(dateiname).bufferedReader().use { it.readText() }
            return ausJson(text)
        }

        fun ausJson(text: String): Katalog {
            val wurzel = JSONObject(text)
            val kategorienJson = wurzel.getJSONArray("kategorien")
            val kategorien = (0 until kategorienJson.length()).map { i ->
                val kat = kategorienJson.getJSONObject(i)
                val befehleJson = kat.getJSONArray("befehle")
                val befehle = (0 until befehleJson.length()).map { j ->
                    val b = befehleJson.getJSONObject(j)
                    val hu = b.getJSONArray("headunits")
                    Befehl(
                        id = b.getString("id"),
                        titel = b.getString("titel"),
                        command = b.getString("command"),
                        headunits = (0 until hu.length()).map { hu.getString(it) },
                        hinweis = b.optString("hinweis", ""),
                    )
                }
                Kategorie(kat.getString("id"), kat.getString("titel"), befehle)
            }
            return Katalog(
                version = wurzel.optInt("version", 1),
                beschreibung = wurzel.optString("beschreibung", ""),
                kategorien = kategorien,
            )
        }
    }
}
