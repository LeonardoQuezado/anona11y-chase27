package com.accessibility.test

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp

// =============================================================
// TELA DE CALIBRAÇÃO #2 — CalibracaoDefeitosScreen (controle positivo)
// Um defeito plantado por checagem, ao lado de controles corretos
// (que NÃO devem ser apontados). Mede se cada analisador encontra
// exatamente o que foi plantado.
//
//   D1  OutlinedTextField(phone) sem label   → LINT TF 1 · STATIC TF 1 · ATF ST 1
//   D2  IconButton { Icon(Settings, null) }  → LINT IN 1 · STATIC IN 1 + IB 1 · ATF ST 1
//   D3  Box 24dp clicável (com descrição)    → STATIC TT 1 (ATF TT 0: o Compose
//       estende a área de toque para 48dp em tempo de execução; o tamanho
//       declarado continua pequeno e é contado pela regra estática)
//   D4  Texto #C8C8C8 sobre branco (~1,7:1)  → ATF CT 1
//
//   Controles corretos (não devem ser apontados):
//     OutlinedTextField(email) com label
//     IconButton { Icon(Share, "Share") }
//     Button { Text("Save") }
//
// Esperado: LINT 2 (1 TF + 1 IN) · STATIC 4 (1 TF + 1 IN + 1 IB + 1 TT)
//           ATF 3 (ST 2 · CT 1)
// Histórico: o gabarito original previa ATF TT 1; a calibração de 26/10
// deu ATF TT 0, e o TT passou a ser medido pela regra estática.
// =============================================================

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    DefectsScreen()
                }
            }
        }
    }
}

@Composable
fun DefectsScreen() {
    var email by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text(text = "Contact details", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.semantics { heading() })
        Spacer(modifier = Modifier.height(24.dp))

        // Controle: campo com label
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Email") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(modifier = Modifier.height(16.dp))

        // D1: campo sem label
        OutlinedTextField(
            value = phone,
            onValueChange = { phone = it },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(modifier = Modifier.height(24.dp))

        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceEvenly,
            modifier = Modifier.fillMaxWidth(),
        ) {
            // D2: botão de ícone sem descrição
            IconButton(onClick = { }) {
                Icon(imageVector = Icons.Filled.Settings, contentDescription = null)
            }
            // Controle: botão de ícone com descrição
            IconButton(onClick = { }) {
                Icon(imageVector = Icons.Filled.Share, contentDescription = "Share")
            }
            // D3: alvo de toque de 24dp
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(24.dp)
                    .clickable { }
                    .semantics { contentDescription = "Close" },
            ) {
                Icon(imageVector = Icons.Filled.Close, contentDescription = "Close", modifier = Modifier.size(18.dp))
            }
        }
        Spacer(modifier = Modifier.height(24.dp))

        // D4: texto de baixo contraste sobre fundo branco fixo
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.White)
                .padding(16.dp),
        ) {
            Text(text = "Your changes are saved automatically", color = Color(0xFFC8C8C8))
        }
        Spacer(modifier = Modifier.height(24.dp))

        // Controle: botão com texto
        Button(onClick = { }, modifier = Modifier.fillMaxWidth().height(52.dp)) {
            Text(text = "Save")
        }
    }
}
