package com.accessibility.test

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp

// =============================================================
// TELA DE CALIBRAÇÃO #3 — CalibracaoCoberturaScreen (cobertura das regras)
// Cada regra da Melodie recebe defeitos em variações de escrita
// (nome/posição, várias linhas, repeat, ordem de modificadores,
// abaixo da dobra), cada um com um controle correto ao lado.
// Também traz pontos cegos conhecidos, que nenhum analisador deve
// apontar, e casos de política (contam por decisão de método).
//
// Contagem: LINT e STATIC contam ocorrências no código; o ATF conta
// elementos renderizados (um repeat(3) vale 1 no código e 3 no ATF).
//
//  A. Rótulos de campos
//   A1 OutlinedTextField sem label (nomeado)   → LINT TF 1 · STATIC TF 1 · ATF ST 1
//   A2 TextField(valor, callback) sem label    → LINT TF 1 · STATIC TF 1 · ATF ST 1
//   A3 OutlinedTextField só com placeholder    → LINT TF 1 · STATIC 0 (o scanner
//      aceita placeholder) · ATF ST a medir
//   Controles: OutlinedTextField e TextField com label → 0
//
//  B. Descrições
//   B1 IconButton { Icon(Settings, contentDescription = null) }
//                                              → LINT IN 1 · STATIC IN 1 + IB 1 · ATF ST 1
//   B2 repeat(3) { IconButton { Icon(Delete, null) } } (posicional)
//                                              → LINT IN 1 · STATIC IN 1 + IB 1 · ATF ST 3
//   B3 Box clicável com Image(contentDescription = null), sem texto
//                                              → LINT IMG 1 · STATIC IMG 1 · ATF ST 1
//   P1 Icon(Info, null) decorativo ao lado de Text("Tips") — POLÍTICA:
//      as regras apontam todo ícone null      → LINT IN 1 · STATIC IN 1 · ATF 0
//   Controles: IconButton com descrição; Box clicável com Image descrita → 0
//
//  C. Alvos de toque (o Compose amplia a área de toque: ATF TT esperado 0)
//   T1 Box size(24.dp).clickable               → STATIC TT 1
//   T2 Box size(48.dp).padding(12.dp).clickable (área 24dp)
//                                              → STATIC TT 1
//   T3 repeat(3) { IconButton(modifier = Modifier.size(32.dp)) }
//                                              → STATIC TT 1 · ATF TT a medir
//   T4 Button(modifier = …height(36.dp))       → STATIC TT 1
//   Controles: clickable.padding(12.dp).size(24.dp) (área 48dp);
//              Row heightIn(min = 48.dp).toggleable + Checkbox(null) → 0
//
//  D. Contraste (abaixo da dobra: exige rolar a tela)
//   K1 #C8C8C8 sobre branco (~1,7:1)           → ATF CT 1
//   K2 #999999 sobre branco (~2,8:1)           → ATF CT 1
//   K3 #8A8A8A sobre branco (~3,4:1) — POLÍTICA: aviso "borderline"
//      do ATF não é contado                    → ATF CT 0 (estimativa pode variar)
//   Controle: #616161 sobre branco (~6,2:1)    → 0
//
//  E. Pontos cegos (nenhum analisador deve apontar — limites conhecidos)
//   X3 Box clicável "Wi-Fi" que muda só a cor, sem estado anunciado
//   X4 Box com pointerInput(detectTapGestures): invisível ao TalkBack
//   X5 Icon(Star, "Favorites") ao lado de Text("Favorites"): descrição
//      redundante (o leitor lê duas vezes) — não detectada
//   (X1 e X2 eram pontos cegos até a v2.5; viraram as regras V e H da v2.6)
//
//  F. Títulos, descrições, foco e campos (regras da v2.6)
//   H1 Text("Account", headlineSmall) sem heading        → STATIC HD 1
//      Controles: os outros 5 títulos com semantics { heading() } → 0
//   V1 IconButton { Icon(Delete, contentDescription = "icon") }   → STATIC VD 1
//   V2 IconButton { Icon(Settings, "Settings button") } (posicional) → STATIC VD 1
//   V3 Image(Person, contentDescription = "Avatar placeholder")    → STATIC VD 1
//      Controles: "Share", "Profile photo", "Close banner", "Dismiss" → 0
//   F1 if (editing) { Button(Done) } else { Button(Edit details) },
//      o botão muda `editing` e some                     → STATIC FOCUS 1
//      Controle: if/else que só troca textos              → 0
//   D1 OutlinedTextField(enabled = editing) mostrando dado → ALÉM DA WCAG 1
//      (conta à parte, fora do total)
//      Controle: OutlinedTextField(readOnly = !editing)   → 0
//
//  Fora do escopo do Compose (só no gabarito): regras do lint Android
//  para XML/Views (LabelFor, ClickableViewAccessibility…); Icon sem o
//  parâmetro contentDescription (não compila).
//
// Esperado (v2.6): LINT 7 (3 TF + 3 IN + 1 IMG)
//           STATIC 17 (2 TF + 3 IN + 2 IB + 1 IMG + 4 TT + 1 HD + 3 VD + 1 FOCUS)
//           ALÉM DA WCAG 1 (D1), fora do total
//           ATF 14 (ST 7 · TT 5 · CT 2)
// Histórico (v2.2–v2.5):
//
// Medido no aparelho (26/10, v2.3 deduplicado = v2.4):
//   LINT 7 ✔ · STATIC 12 ✔ · pontos cegos e controles 0 ✔
//   ATF 14 = ST 7 ✔ · CT 2 ✔ · TT 5
//   A3 (só placeholder): ATF 0 — o ATF aceita o placeholder como texto
//   TT no ATF: T1 0 (o Compose ampliou para 48dp, havia espaço);
//     T2 1 (40dp), T3 3 (32–33dp), T4 1 (42dp) — a ampliação do Compose
//     é limitada pelos vizinhos, então o ATF às vezes aponta. O TT
//     estático aponta os 4 no código, independentemente disso.
// =============================================================

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    CoverageScreen()
                }
            }
        }
    }
}

@Composable
fun CoverageScreen() {
    var name by remember { mutableStateOf("") }
    var city by remember { mutableStateOf("") }
    var nickname by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var search by remember { mutableStateOf("") }
    var subscribed by remember { mutableStateOf(false) }
    var wifiOn by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf(false) }
    var country by remember { mutableStateOf("Brazil") }
    var region by remember { mutableStateOf("Ceará") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
    ) {
        // H1: título sem semântica de heading
        Text(text = "Account", style = MaterialTheme.typography.headlineSmall)
        Spacer(modifier = Modifier.height(12.dp))

        // Controle A
        OutlinedTextField(
            value = name,
            onValueChange = { name = it },
            label = { Text("Full name") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        // A1
        OutlinedTextField(
            value = nickname,
            onValueChange = { nickname = it },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        // A2
        TextField(phone, { phone = it }, modifier = Modifier.fillMaxWidth())
        // Controle A
        TextField(value = city, onValueChange = { city = it }, label = { Text("City") }, modifier = Modifier.fillMaxWidth())
        // A3
        OutlinedTextField(
            value = search,
            onValueChange = { search = it },
            placeholder = { Text("Search contacts") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(modifier = Modifier.height(16.dp))

        Text(text = "Actions", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.semantics { heading() })
        Row(verticalAlignment = Alignment.CenterVertically) {
            // B1
            IconButton(onClick = { }) {
                Icon(imageVector = Icons.Filled.Settings, contentDescription = null)
            }
            // B2
            repeat(3) {
                IconButton(onClick = { }) {
                    Icon(Icons.Filled.Delete, null)
                }
            }
            // Controle B
            IconButton(onClick = { }) {
                Icon(imageVector = Icons.Filled.Share, contentDescription = "Share")
            }
            // V1
            IconButton(onClick = { }) {
                Icon(imageVector = Icons.Filled.Delete, contentDescription = "icon")
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            // B3
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier.size(72.dp).background(Color.LightGray).clickable { },
            ) {
                Image(imageVector = Icons.Filled.Person, contentDescription = null)
            }
            // Controle B
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier.size(72.dp).background(Color.LightGray).clickable { },
            ) {
                Image(imageVector = Icons.Filled.Person, contentDescription = "Profile photo")
            }
            // P1
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.Info, null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = "Tips")
            }
        }
        Spacer(modifier = Modifier.height(16.dp))

        Text(text = "Touch targets", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.semantics { heading() })
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(24.dp)) {
            // T1
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(24.dp)
                    .clickable { }
                    .semantics { contentDescription = "Close banner" },
            ) {
                Icon(imageVector = Icons.Filled.Close, contentDescription = "Close banner", modifier = Modifier.size(18.dp))
            }
            // T2
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier.size(48.dp).padding(12.dp).clickable { },
            ) {
                Icon(imageVector = Icons.Filled.Close, contentDescription = "Close dialog")
            }
            // Controle C: área clicável de 48dp (padding dentro do clickable)
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier.clickable { }.padding(12.dp).size(24.dp),
            ) {
                Icon(imageVector = Icons.Filled.Close, contentDescription = "Dismiss")
            }
        }
        Row {
            // T3
            repeat(3) {
                IconButton(onClick = { }, modifier = Modifier.size(32.dp)) {
                    Icon(imageVector = Icons.Filled.Star, contentDescription = "Favorite")
                }
            }
        }
        // T4
        Button(onClick = { }, modifier = Modifier.fillMaxWidth().height(36.dp)) {
            Text(text = "Continue")
        }
        // Controle C
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp)
                .toggleable(value = subscribed, onValueChange = { subscribed = it }, role = Role.Checkbox),
        ) {
            Checkbox(checked = subscribed, onCheckedChange = null)
            Spacer(modifier = Modifier.width(12.dp))
            Text(text = "Subscribe to updates")
        }
        Spacer(modifier = Modifier.height(16.dp))

        Text(text = "Labels and state", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.semantics { heading() })
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            // V2
            IconButton(onClick = { }) {
                Icon(Icons.Filled.Settings, "Settings button")
            }
            // V3
            Image(imageVector = Icons.Filled.Person, contentDescription = "Avatar placeholder", modifier = Modifier.size(48.dp))
            // X5
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(imageVector = Icons.Filled.Star, contentDescription = "Favorites")
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = "Favorites")
            }
        }
        // F1
        if (editing) {
            Button(onClick = { editing = false }, modifier = Modifier.fillMaxWidth()) {
                Text(text = "Done")
            }
        } else {
            Button(onClick = { editing = true }, modifier = Modifier.fillMaxWidth()) {
                Text(text = "Edit details")
            }
        }
        // Controle F
        if (subscribed) {
            Text(text = "You are subscribed")
        } else {
            Text(text = "You are not subscribed")
        }
        // D1
        OutlinedTextField(
            value = country,
            onValueChange = { country = it },
            label = { Text("Country") },
            enabled = editing,
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        // Controle D
        OutlinedTextField(
            value = region,
            onValueChange = { region = it },
            label = { Text("Region") },
            readOnly = !editing,
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(modifier = Modifier.height(16.dp))

        Text(text = "Blind spots", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.semantics { heading() })
        // X3
        Box(
            contentAlignment = Alignment.CenterStart,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp)
                .background(if (wifiOn) Color(0xFF1B5E20) else Color(0xFF424242))
                .clickable { wifiOn = !wifiOn }
                .padding(horizontal = 16.dp),
        ) {
            Text(text = "Wi-Fi", color = Color.White)
        }
        Spacer(modifier = Modifier.height(8.dp))
        // X4
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
                .background(Color(0xFF3949AB))
                .pointerInput(Unit) { detectTapGestures { } },
        )
        Spacer(modifier = Modifier.height(320.dp))

        Text(text = "Contrast", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.semantics { heading() })
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.White)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // K1
            Text(text = "Saved automatically", color = Color(0xFFC8C8C8))
            // K2
            Text(text = "Last synced yesterday", color = Color(0xFF999999))
            // K3
            Text(text = "Version 2.4.1", color = Color(0xFF8A8A8A))
            // Controle D
            Text(text = "Storage almost full", color = Color(0xFF616161))
        }
        Spacer(modifier = Modifier.height(48.dp))
    }
}
