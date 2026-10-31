package com.bmwhuinfo

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import com.bmwhuinfo.ui.DiagnoseScreen
import com.bmwhuinfo.ui.DiagnoseViewModel

class MainActivity : ComponentActivity() {

    private val viewModel: DiagnoseViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface {
                    DiagnoseScreen(viewModel)
                }
            }
        }
    }
}
