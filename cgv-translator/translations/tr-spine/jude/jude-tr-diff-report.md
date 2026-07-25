# Jude TR spine (Robinson-parsed)

Textual basis: **Scrivener 1894 TR** via `robinson-parsed/JUDE.UTR`.
Morph/Strong’s: Maurice A. Robinson. MorphGNT used only for lemma fill + phrase remap.

## Stats

- Verses: 25
- TR tokens: 454
- MorphGNT tokens: 459
- Verses identical after fold vs MorphGNT: 9
- Verses with zero Morph ops: 9
- TR-only tokens: 18
- Morph-only tokens: 23
- Substitutions: 13
- Accents from tr1894.txt: 444
- Surfaces from beta: 10
- Lemmas filled from MorphGNT: 436
- Phrases remapped: 51
- Phrase issues: 9

## Verses with TR ≠ MorphGNT (token-level ops)

### Jude 1:1

- identicalFold: False
- TR tokens: 17 · Morph tokens: 17
- TR: Ἰούδας Ἰησοῦ Χριστοῦ δοῦλος ἀδελφὸς δὲ Ἰακώβου τοῖς ἐν Θεῷ πατρὶ ἠγίασμένοις καὶ Ἰησοῦ Χριστῷ τετηρημένοις κλητοῖς
- Morph: Ἰούδας Ἰησοῦ Χριστοῦ δοῦλος ἀδελφὸς δὲ Ἰακώβου τοῖς ἐν θεῷ πατρὶ ἠγαπημένοις καὶ Ἰησοῦ Χριστῷ τετηρημένοις κλητοῖς

Ops:
- `substitute`: TR=`ἠγίασμένοις` · Morph=`ἠγαπημένοις`

### Jude 1:3

- identicalFold: False
- TR tokens: 22 · Morph tokens: 23
- TR: Ἀγαπητοί πᾶσαν σπουδὴν ποιούμενος γράφειν ὑμῖν περὶ τῆς κοινῆς σωτηρίας ἀνάγκην ἔσχον γράψαι ὑμῖν παρακαλῶν ἐπαγωνίζεσθαι τῇ ἅπαξ παραδοθείσῃ τοῖς ἁγίοις πίστει
- Morph: Ἀγαπητοί πᾶσαν σπουδὴν ποιούμενος γράφειν ὑμῖν περὶ τῆς κοινῆς ἡμῶν σωτηρίας ἀνάγκην ἔσχον γράψαι ὑμῖν παρακαλῶν ἐπαγωνίζεσθαι τῇ ἅπαξ παραδοθείσῃ τοῖς ἁγίοις πίστει

Ops:
- `morph_only`: TR=`` · Morph=`ἡμῶν`

### Jude 1:4

- identicalFold: False
- TR tokens: 31 · Morph tokens: 30
- TR: παρεισέδυσαν γάρ τινες ἄνθρωποι οἱ πάλαι προγεγραμμένοι εἰς τοῦτο τὸ κρίμα ἀσεβεῖς τὴν τοῦ Θεοῦ ἡμῶν χάριν μετατιθέντες εἰς ἀσέλγειαν καὶ τὸν μόνον δεσπότην Θεόν καὶ Κύριον ἡμῶν Ἰησοῦν Χριστὸν ἀρνούμενοι
- Morph: παρεισέδυσαν γάρ τινες ἄνθρωποι οἱ πάλαι προγεγραμμένοι εἰς τοῦτο τὸ κρίμα ἀσεβεῖς τὴν τοῦ θεοῦ ἡμῶν χάριτα μετατιθέντες εἰς ἀσέλγειαν καὶ τὸν μόνον δεσπότην καὶ κύριον ἡμῶν Ἰησοῦν Χριστὸν ἀρνούμενοι

Ops:
- `substitute`: TR=`χάριν` · Morph=`χάριτα`
- `tr_only`: TR=`Θεόν` · Morph=``

### Jude 1:5

- identicalFold: False
- TR tokens: 22 · Morph tokens: 21
- TR: Ὑπομνῆσαι δὲ ὑμᾶς βούλομαι εἰδότας ὑμᾶς ἅπαξ τοῦτο ὅτι ο Κύριος λαὸν ἐκ γῆς Αἰγύπτου σώσας τὸ δεύτερον τοὺς μὴ πιστεύσαντας ἀπώλεσεν
- Morph: Ὑπομνῆσαι δὲ ὑμᾶς βούλομαι εἰδότας ὑμᾶς ἅπαξ πάντα ὅτι Ἰησοῦς λαὸν ἐκ γῆς Αἰγύπτου σώσας τὸ δεύτερον τοὺς μὴ πιστεύσαντας ἀπώλεσεν

Ops:
- `substitute`: TR=`τοῦτο` · Morph=`πάντα`
- `substitute`: TR=`ο` · Morph=`Ἰησοῦς`
- `tr_only`: TR=`Κύριος` · Morph=``

### Jude 1:7

- identicalFold: False
- TR tokens: 25 · Morph tokens: 25
- TR: ὡς Σόδομα καὶ Γόμορρα καὶ αἱ περὶ αὐτὰς πόλεις τὸν ὅμοιον τούτοις τρόπον ἐκπορνεύσασαι καὶ ἀπελθοῦσαι ὀπίσω σαρκὸς ἑτέρας πρόκεινται δεῖγμα πυρὸς αἰωνίου δίκην ὑπέχουσαι
- Morph: ὡς Σόδομα καὶ Γόμορρα καὶ αἱ περὶ αὐτὰς πόλεις τὸν ὅμοιον τρόπον τούτοις ἐκπορνεύσασαι καὶ ἀπελθοῦσαι ὀπίσω σαρκὸς ἑτέρας πρόκεινται δεῖγμα πυρὸς αἰωνίου δίκην ὑπέχουσαι

Ops:
- `morph_only`: TR=`` · Morph=`τρόπον`
- `tr_only`: TR=`τρόπον` · Morph=``

### Jude 1:9

- identicalFold: False
- TR tokens: 24 · Morph tokens: 24
- TR: ὁ δὲ Μιχαὴλ ο ἀρχάγγελος ὅτε τῷ διαβόλῳ διακρινόμενος διελέγετο περὶ τοῦ Μωσέως σώματος οὐκ ετολμησεν κρίσιν ἐπενεγκεῖν βλασφημίας ἀλλ’ εἶπεν Ἐπιτιμήσαι σοι Κύριος
- Morph: ὁ δὲ Μιχαὴλ ὁ ἀρχάγγελος ὅτε τῷ διαβόλῳ διακρινόμενος διελέγετο περὶ τοῦ Μωϋσέως σώματος οὐκ ἐτόλμησεν κρίσιν ἐπενεγκεῖν βλασφημίας ἀλλὰ εἶπεν Ἐπιτιμήσαι σοι κύριος

Ops:
- `substitute`: TR=`Μωσέως` · Morph=`Μωϋσέως`
- `substitute`: TR=`ἀλλ’` · Morph=`ἀλλὰ`

### Jude 1:12

- identicalFold: False
- TR tokens: 23 · Morph tokens: 23
- TR: οὗτοί εἰσιν ἐν ταῖς ἀγάπαις ὑμῶν σπιλάδες συνευωχούμενοι ὑμῖν ἀφόβως ἑαυτοὺς ποιμαίνοντες νεφέλαι ἄνυδροι ὑπὸ ἀνέμων περιφερόμεναι δένδρα φθινοπωρινὰ ἄκαρπα δὶς ἀποθανόντα ἐκριζωθέντα
- Morph: οὗτοί εἰσιν οἱ ἐν ταῖς ἀγάπαις ὑμῶν σπιλάδες συνευωχούμενοι ἀφόβως ἑαυτοὺς ποιμαίνοντες νεφέλαι ἄνυδροι ὑπὸ ἀνέμων παραφερόμεναι δένδρα φθινοπωρινὰ ἄκαρπα δὶς ἀποθανόντα ἐκριζωθέντα

Ops:
- `morph_only`: TR=`` · Morph=`οἱ`
- `tr_only`: TR=`ὑμῖν` · Morph=``
- `substitute`: TR=`περιφερόμεναι` · Morph=`παραφερόμεναι`

### Jude 1:13

- identicalFold: False
- TR tokens: 18 · Morph tokens: 17
- TR: κύματα ἄγρια θαλάσσης ἐπαφρίζοντα τὰς ἑαυτῶν αἰσχύνας ἀστέρες πλανῆται οἷς ο ζόφος τοῦ σκότους εἰς τὸν αἰῶνα τετήρηται
- Morph: κύματα ἄγρια θαλάσσης ἐπαφρίζοντα τὰς ἑαυτῶν αἰσχύνας ἀστέρες πλανῆται οἷς ὁ ζόφος τοῦ σκότους εἰς αἰῶνα τετήρηται

Ops:
- `tr_only`: TR=`τὸν` · Morph=``

### Jude 1:14

- identicalFold: False
- TR tokens: 16 · Morph tokens: 16
- TR: προεφητευσεν δὲ καὶ τούτοις ἕβδομος ἀπὸ Ἀδὰμ Ἑνὼχ λέγων Ἰδοὺ ηλθεν Κύριος ἐν μυριάσιν ἁγίαις αὐτοῦ
- Morph: Προεφήτευσεν δὲ καὶ τούτοις ἕβδομος ἀπὸ Ἀδὰμ Ἑνὼχ λέγων Ἰδοὺ ἦλθεν κύριος ἐν ἁγίαις μυριάσιν αὐτοῦ

Ops:
- `morph_only`: TR=`` · Morph=`ἁγίαις`
- `tr_only`: TR=`ἁγίαις` · Morph=``

### Jude 1:15

- identicalFold: False
- TR tokens: 29 · Morph tokens: 28
- TR: ποιῆσαι κρίσιν κατὰ πάντων καὶ ἐξἐλέγξαι πάντας τοὺς ἀσεβεῖς αὐτῶν περὶ πάντων τῶν ἔργων ἀσεβείας αὐτῶν ὧν ἠσέβησαν καὶ περὶ πάντων τῶν σκληρῶν ὧν ἐλάλησαν κατ’ αὐτοῦ ἁμαρτωλοὶ ἀσεβεῖς
- Morph: ποιῆσαι κρίσιν κατὰ πάντων καὶ ἐλέγξαι πάντας τοὺς ἀσεβεῖς περὶ πάντων τῶν ἔργων ἀσεβείας αὐτῶν ὧν ἠσέβησαν καὶ περὶ πάντων τῶν σκληρῶν ὧν ἐλάλησαν κατ’ αὐτοῦ ἁμαρτωλοὶ ἀσεβεῖς

Ops:
- `substitute`: TR=`ἐξἐλέγξαι` · Morph=`ἐλέγξαι`
- `tr_only`: TR=`αὐτῶν` · Morph=``

### Jude 1:18

- identicalFold: False
- TR tokens: 16 · Morph tokens: 15
- TR: ὅτι ἔλεγον ὑμῖν ὅτι ἐν ἐσχάτῳ χρόνῳ ἔσονται ἐμπαῖκται κατὰ τὰς ἑαυτῶν ἐπιθυμίας πορευόμενοι τῶν ἀσεβειῶν
- Morph: ὅτι ἔλεγον ὑμῖν Ἐπ’ ἐσχάτου χρόνου ἔσονται ἐμπαῖκται κατὰ τὰς ἑαυτῶν ἐπιθυμίας πορευόμενοι τῶν ἀσεβειῶν

Ops:
- `substitute`: TR=`ὅτι` · Morph=`Ἐπ’`
- `substitute`: TR=`ἐν` · Morph=`ἐσχάτου`
- `substitute`: TR=`ἐσχάτῳ` · Morph=`χρόνου`
- `tr_only`: TR=`χρόνῳ` · Morph=``

### Jude 1:19

- identicalFold: False
- TR tokens: 9 · Morph tokens: 8
- TR: οὗτοί εἰσιν οἱ ἀποδιορίζοντες ἑαυτούς ψυχικοί Πνεῦμα μὴ ἔχοντες
- Morph: οὗτοί εἰσιν οἱ ἀποδιορίζοντες ψυχικοί πνεῦμα μὴ ἔχοντες

Ops:
- `tr_only`: TR=`ἑαυτούς` · Morph=``

### Jude 1:20

- identicalFold: False
- TR tokens: 13 · Morph tokens: 13
- TR: ὑμεῖς δέ ἀγαπητοί τῇ ἁγιωτάτῃ ὑμῶν πίστει ἐποικοδομοῦντες ἑαυτοὺς ἐν Πνεύματι Ἁγίω προσευχόμενοι
- Morph: ὑμεῖς δέ ἀγαπητοί ἐποικοδομοῦντες ἑαυτοὺς τῇ ἁγιωτάτῃ ὑμῶν πίστει ἐν πνεύματι ἁγίῳ προσευχόμενοι

Ops:
- `morph_only`: TR=`` · Morph=`ἐποικοδομοῦντες`
- `morph_only`: TR=`` · Morph=`ἑαυτοὺς`
- `tr_only`: TR=`ἐποικοδομοῦντες` · Morph=``
- `tr_only`: TR=`ἑαυτοὺς` · Morph=``

### Jude 1:22

- identicalFold: False
- TR tokens: 5 · Morph tokens: 5
- TR: καὶ οὓς μὲν ἐλεεῖτε διακρινομένοι
- Morph: καὶ οὓς μὲν ἐλεᾶτε διακρινομένους

Ops:
- `substitute`: TR=`ἐλεεῖτε` · Morph=`ἐλεᾶτε`
- `substitute`: TR=`διακρινομένοι` · Morph=`διακρινομένους`

### Jude 1:23

- identicalFold: False
- TR tokens: 17 · Morph tokens: 19
- TR: οὓς δὲ ἐν φόβῳ σώζετε ἐκ τοῦ πυρὸς ἁρπάζοντες μισοῦντες καὶ τὸν ἀπὸ τῆς σαρκὸς ἐσπιλωμένον χιτῶνα
- Morph: οὓς δὲ σῴζετε ἐκ πυρὸς ἁρπάζοντες οὓς δὲ ἐλεᾶτε ἐν φόβῳ μισοῦντες καὶ τὸν ἀπὸ τῆς σαρκὸς ἐσπιλωμένον χιτῶνα

Ops:
- `morph_only`: TR=`` · Morph=`σῴζετε`
- `morph_only`: TR=`` · Morph=`ἐκ`
- `morph_only`: TR=`` · Morph=`πυρὸς`
- `morph_only`: TR=`` · Morph=`ἁρπάζοντες`
- `morph_only`: TR=`` · Morph=`οὓς`
- `morph_only`: TR=`` · Morph=`δὲ`
- `morph_only`: TR=`` · Morph=`ἐλεᾶτε`
- `tr_only`: TR=`σώζετε` · Morph=``
- `tr_only`: TR=`ἐκ` · Morph=``
- `tr_only`: TR=`τοῦ` · Morph=``
- `tr_only`: TR=`πυρὸς` · Morph=``
- `tr_only`: TR=`ἁρπάζοντες` · Morph=``

### Jude 1:25

- identicalFold: False
- TR tokens: 19 · Morph tokens: 27
- TR: μόνῳ σοφῷ Θεῷ σωτῆρι ἡμῶν δόξα καὶ μεγαλωσύνη κράτος καὶ ἐξουσία καὶ νῦν καὶ εἰς πάντας τοὺς αἰῶνας ἀμήν
- Morph: μόνῳ θεῷ σωτῆρι ἡμῶν διὰ Ἰησοῦ Χριστοῦ τοῦ κυρίου ἡμῶν δόξα μεγαλωσύνη κράτος καὶ ἐξουσία πρὸ παντὸς τοῦ αἰῶνος καὶ νῦν καὶ εἰς πάντας τοὺς αἰῶνας ἀμήν

Ops:
- `tr_only`: TR=`σοφῷ` · Morph=``
- `morph_only`: TR=`` · Morph=`διὰ`
- `morph_only`: TR=`` · Morph=`Ἰησοῦ`
- `morph_only`: TR=`` · Morph=`Χριστοῦ`
- `morph_only`: TR=`` · Morph=`τοῦ`
- `morph_only`: TR=`` · Morph=`κυρίου`
- `morph_only`: TR=`` · Morph=`ἡμῶν`
- `tr_only`: TR=`καὶ` · Morph=``
- `morph_only`: TR=`` · Morph=`πρὸ`
- `morph_only`: TR=`` · Morph=`παντὸς`
- `morph_only`: TR=`` · Morph=`τοῦ`
- `morph_only`: TR=`` · Morph=`αἰῶνος`

## Phrase remap issues

- phrase 3 Jude 1:3: morph positions not in TR alignment [10]
  - ES: Amados, poniéndome toda diligencia en escribirles acerca de nuestra común salvación,
  - GR(old): Ἀγαπητοί πᾶσαν σπουδὴν ποιούμενος γράφειν ὑμῖν περὶ τῆς κοινῆς ἡμῶν σωτηρίας
- phrase 13 Jude 1:7: morph positions not in TR alignment [12]
  - ES: las cuales de la misma manera que aquellos se entregaron a la fornicación y fueron tras carne extraña,
  - GR(old): τὸν ὅμοιον τρόπον τούτοις ἐκπορνεύσασαι καὶ ἀπελθοῦσαι ὀπίσω σαρκὸς ἑτέρας
- phrase 25 Jude 1:12: morph positions not in TR alignment [3]
  - ES: Estos son escollos en sus ágapes, banqueteando con ustedes sin temor, apacentándose a sí mismos;
  - GR(old): οὗτοί εἰσιν οἱ ἐν ταῖς ἀγάπαις ὑμῶν σπιλάδες συνευωχούμενοι ἀφόβως ἑαυτοὺς ποιμαίνοντες
- phrase 31 Jude 1:14: morph positions not in TR alignment [14]
  - ES: «He aquí, el Señor vino con sus santas miríadas,
  - GR(old): Ἰδοὺ ἦλθεν κύριος ἐν ἁγίαις μυριάσιν αὐτοῦ
- phrase 40 Jude 1:20: morph positions not in TR alignment [4, 5]
  - ES: Pero ustedes, amados, edificándose sobre su santísima fe,
  - GR(old): ὑμεῖς δέ ἀγαπητοί ἐποικοδομοῦντες ἑαυτοὺς τῇ ἁγιωτάτῃ ὑμῶν πίστει
- phrase 45 Jude 1:23: morph positions not in TR alignment [3, 4, 5, 6]
  - ES: a otros sálvenlos arrebatándolos del fuego;
  - GR(old): οὓς δὲ σῴζετε ἐκ πυρὸς ἁρπάζοντες
- phrase 46 Jude 1:23: morph positions not in TR alignment [7, 8, 9]
  - ES: y a otros tengan misericordia con temor, aborreciendo aun la ropa contaminada por la carne.
  - GR(old): οὓς δὲ ἐλεᾶτε ἐν φόβῳ μισοῦντες καὶ τὸν ἀπὸ τῆς σαρκὸς ἐσπιλωμένον χιτῶνα
- phrase 48 Jude 1:25: morph positions not in TR alignment [5, 6, 7, 8, 9, 10]
  - ES: al único Dios, nuestro Salvador, por medio de Jesús Cristo nuestro Señor,
  - GR(old): μόνῳ θεῷ σωτῆρι ἡμῶν διὰ Ἰησοῦ Χριστοῦ τοῦ κυρίου ἡμῶν
- phrase 49 Jude 1:25: morph positions not in TR alignment [16, 17, 18, 19]
  - ES: sea gloria, majestad, dominio y autoridad, antes de todo el siglo, y ahora, y por todos los siglos.
  - GR(old): δόξα μεγαλωσύνη κράτος καὶ ἐξουσία πρὸ παντὸς τοῦ αἰῶνος καὶ νῦν καὶ εἰς πάντας τοὺς αἰῶνας
