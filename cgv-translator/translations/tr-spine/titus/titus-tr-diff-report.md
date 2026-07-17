# Titus TR spine (Robinson-parsed)

Textual basis: **Scrivener 1894 TR** via `robinson-parsed/TIT.UTR`.
Morph/Strong’s: Maurice A. Robinson. MorphGNT used only for lemma fill + phrase remap.

## Stats

- Verses: 46
- TR tokens: 665
- MorphGNT tokens: 659
- Verses identical after fold vs MorphGNT: 28
- Verses with zero Morph ops: 28
- TR-only tokens: 10
- Morph-only tokens: 4
- Substitutions: 15
- Accents from tr1894.txt: 639
- Surfaces from beta: 26
- Lemmas filled from MorphGNT: 655
- Phrases remapped: 94
- Phrase issues: 0

## Verses with TR ≠ MorphGNT (token-level ops)

### Titus 1:4

- identicalFold: False
- TR tokens: 19 · Morph tokens: 18
- TR: Τίτῳ γνησίῳ τέκνῳ κατὰ κοινὴν πίστιν χάρις ἔλεος εἰρήνη ἀπὸ Θεοῦ πατρὸς καὶ Κυρίου Ἰησοῦ Χριστοῦ τοῦ σωτῆρος ἡμῶν
- Morph: Τίτῳ γνησίῳ τέκνῳ κατὰ κοινὴν πίστιν χάρις καὶ εἰρήνη ἀπὸ θεοῦ πατρὸς καὶ Χριστοῦ Ἰησοῦ τοῦ σωτῆρος ἡμῶν

Ops:
- `substitute`: TR=`ἔλεος` · Morph=`καὶ`
- `substitute`: TR=`Κυρίου` · Morph=`Χριστοῦ`
- `tr_only`: TR=`Χριστοῦ` · Morph=``

### Titus 1:5

- identicalFold: False
- TR tokens: 19 · Morph tokens: 19
- TR: Τούτου χάριν κατέλιπόν σε ἐν Κρήτῃ ἵνα τὰ λείποντα ἐπιδιορθώσῃ καὶ καταστήσῃς κατὰ πόλιν πρεσβυτέρους ὡς ἐγώ σοι διεταξάμην
- Morph: Τούτου χάριν ἀπέλιπόν σε ἐν Κρήτῃ ἵνα τὰ λείποντα ἐπιδιορθώσῃ καὶ καταστήσῃς κατὰ πόλιν πρεσβυτέρους ὡς ἐγώ σοι διεταξάμην

Ops:
- `substitute`: TR=`κατέλιπόν` · Morph=`ἀπέλιπόν`

### Titus 1:10

- identicalFold: False
- TR tokens: 12 · Morph tokens: 13
- TR: εισιν γὰρ πολλοὶ καὶ ἀνυπότακτοι ματαιολόγοι καὶ φρεναπάται μάλιστα οἱ ἐκ περιτομῆς
- Morph: Εἰσὶν γὰρ πολλοὶ καὶ ἀνυπότακτοι ματαιολόγοι καὶ φρεναπάται μάλιστα οἱ ἐκ τῆς περιτομῆς

Ops:
- `morph_only`: TR=`` · Morph=`τῆς`

### Titus 1:15

- identicalFold: False
- TR tokens: 21 · Morph tokens: 20
- TR: πάντα μὲν καθαρὰ τοῖς καθαροῖς τοῖς δὲ μεμιασμένοις καὶ ἀπίστοις οὐδὲν καθαρόν ἀλλὰ μεμίανται αὐτῶν καὶ ο νοῦς καὶ η συνείδησις
- Morph: πάντα καθαρὰ τοῖς καθαροῖς τοῖς δὲ μεμιαμμένοις καὶ ἀπίστοις οὐδὲν καθαρόν ἀλλὰ μεμίανται αὐτῶν καὶ ὁ νοῦς καὶ ἡ συνείδησις

Ops:
- `tr_only`: TR=`μὲν` · Morph=``
- `substitute`: TR=`μεμιασμένοις` · Morph=`μεμιαμμένοις`

### Titus 2:3

- identicalFold: False
- TR tokens: 12 · Morph tokens: 12
- TR: Πρεσβύτιδας ὡσαύτως ἐν καταστήματι ἱεροπρεπεῖς μὴ διαβόλους μὴ οἴνῳ πολλῷ δεδουλωμένας καλοδιδασκάλους
- Morph: Πρεσβύτιδας ὡσαύτως ἐν καταστήματι ἱεροπρεπεῖς μὴ διαβόλους μηδὲ οἴνῳ πολλῷ δεδουλωμένας καλοδιδασκάλους

Ops:
- `substitute`: TR=`μὴ` · Morph=`μηδὲ`

### Titus 2:4

- identicalFold: False
- TR tokens: 7 · Morph tokens: 7
- TR: ἵνα σωφρονιζωσιν τὰς νέας φιλάνδρους εἶναι φιλοτέκνους
- Morph: ἵνα σωφρονίζωσι τὰς νέας φιλάνδρους εἶναι φιλοτέκνους

Ops:
- `substitute`: TR=`σωφρονιζωσιν` · Morph=`σωφρονίζωσι`

### Titus 2:5

- identicalFold: False
- TR tokens: 15 · Morph tokens: 15
- TR: σώφρονας ἁγνάς οἰκουρούς ἀγαθάς ὑποτασσομένας τοῖς ἰδίοις ἀνδράσιν ἵνα μὴ ο λόγος τοῦ Θεοῦ βλασφημῆται
- Morph: σώφρονας ἁγνάς οἰκουργούς ἀγαθάς ὑποτασσομένας τοῖς ἰδίοις ἀνδράσιν ἵνα μὴ ὁ λόγος τοῦ θεοῦ βλασφημῆται

Ops:
- `substitute`: TR=`οἰκουρούς` · Morph=`οἰκουργούς`

### Titus 2:7

- identicalFold: False
- TR tokens: 13 · Morph tokens: 12
- TR: περὶ πάντα σεαυτὸν παρεχόμενος τύπον καλῶν ἔργων ἐν τῇ διδασκαλίᾳ ἀδιἀφθορίαν σεμνότητα ἀφθαρσιαν
- Morph: περὶ πάντα σεαυτὸν παρεχόμενος τύπον καλῶν ἔργων ἐν τῇ διδασκαλίᾳ ἀφθορίαν σεμνότητα

Ops:
- `substitute`: TR=`ἀδιἀφθορίαν` · Morph=`ἀφθορίαν`
- `tr_only`: TR=`ἀφθαρσιαν` · Morph=``

### Titus 2:8

- identicalFold: False
- TR tokens: 14 · Morph tokens: 14
- TR: λόγον ὑγιῆ ἀκατάγνωστον ἵνα ο ἐξ ἐναντίας ἐντραπῇ μηδὲν ἔχων περὶ ὑμῶν λέγειν φαῦλον
- Morph: λόγον ὑγιῆ ἀκατάγνωστον ἵνα ὁ ἐξ ἐναντίας ἐντραπῇ μηδὲν ἔχων λέγειν περὶ ἡμῶν φαῦλον

Ops:
- `morph_only`: TR=`` · Morph=`λέγειν`
- `substitute`: TR=`ὑμῶν` · Morph=`ἡμῶν`
- `tr_only`: TR=`λέγειν` · Morph=``

### Titus 2:10

- identicalFold: False
- TR tokens: 17 · Morph tokens: 18
- TR: μὴ νοσφιζομένους ἀλλὰ πίστιν πᾶσαν ἐνδεικνυμένους ἀγαθήν ἵνα τὴν διδασκαλίαν τοῦ σωτῆρος ἡμῶν Θεοῦ κοσμῶσιν ἐν πᾶσιν
- Morph: μὴ νοσφιζομένους ἀλλὰ πᾶσαν πίστιν ἐνδεικνυμένους ἀγαθήν ἵνα τὴν διδασκαλίαν τὴν τοῦ σωτῆρος ἡμῶν θεοῦ κοσμῶσιν ἐν πᾶσιν

Ops:
- `morph_only`: TR=`` · Morph=`πᾶσαν`
- `tr_only`: TR=`πᾶσαν` · Morph=``
- `morph_only`: TR=`` · Morph=`τὴν`

### Titus 2:11

- identicalFold: False
- TR tokens: 10 · Morph tokens: 9
- TR: ἐπεφάνη γὰρ η χάρις τοῦ Θεοῦ η σωτήριος πᾶσιν ἀνθρώποις
- Morph: Ἐπεφάνη γὰρ ἡ χάρις τοῦ θεοῦ σωτήριος πᾶσιν ἀνθρώποις

Ops:
- `tr_only`: TR=`η` · Morph=``

### Titus 3:1

- identicalFold: False
- TR tokens: 13 · Morph tokens: 12
- TR: Ὑπομίμνησκε αὐτοὺς ἀρχαῖς καὶ ἐξουσίαις ὑποτάσσεσθαι πειθαρχεῖν πρὸς πᾶν ἔργον ἀγαθὸν ἑτοίμους εἶναι
- Morph: Ὑπομίμνῃσκε αὐτοὺς ἀρχαῖς ἐξουσίαις ὑποτάσσεσθαι πειθαρχεῖν πρὸς πᾶν ἔργον ἀγαθὸν ἑτοίμους εἶναι

Ops:
- `tr_only`: TR=`καὶ` · Morph=``

### Titus 3:2

- identicalFold: False
- TR tokens: 11 · Morph tokens: 11
- TR: μηδένα βλασφημεῖν ἀμάχους εἶναι ἐπιεικεῖς πᾶσαν ἐνδεικνυμένους πρᾳότητα πρὸς πάντας ἀνθρώπους
- Morph: μηδένα βλασφημεῖν ἀμάχους εἶναι ἐπιεικεῖς πᾶσαν ἐνδεικνυμένους πραΰτητα πρὸς πάντας ἀνθρώπους

Ops:
- `substitute`: TR=`πρᾳότητα` · Morph=`πραΰτητα`

### Titus 3:5

- identicalFold: False
- TR tokens: 23 · Morph tokens: 23
- TR: οὐκ ἐξ ἔργων τῶν ἐν δικαιοσύνῃ ὧν ἐποιήσαμεν ἡμεῖς ἀλλὰ κατὰ τὸν αὐτοῦ ἔλεον ἔσωσεν ἡμᾶς διὰ λουτροῦ παλιγγενεσίας καὶ ἀνακαινώσεως Πνεύματος Ἁγίου
- Morph: οὐκ ἐξ ἔργων τῶν ἐν δικαιοσύνῃ ἃ ἐποιήσαμεν ἡμεῖς ἀλλὰ κατὰ τὸ αὐτοῦ ἔλεος ἔσωσεν ἡμᾶς διὰ λουτροῦ παλιγγενεσίας καὶ ἀνακαινώσεως πνεύματος ἁγίου

Ops:
- `substitute`: TR=`ὧν` · Morph=`ἃ`
- `substitute`: TR=`τὸν` · Morph=`τὸ`
- `substitute`: TR=`ἔλεον` · Morph=`ἔλεος`

### Titus 3:7

- identicalFold: False
- TR tokens: 11 · Morph tokens: 11
- TR: ἵνα δικαιωθέντες τῇ ἐκείνου χάριτι κληρονόμοι γενώμεθα κατ’ ἐλπίδα ζωῆς αἰωνίου
- Morph: ἵνα δικαιωθέντες τῇ ἐκείνου χάριτι κληρονόμοι γενηθῶμεν κατ’ ἐλπίδα ζωῆς αἰωνίου

Ops:
- `substitute`: TR=`γενώμεθα` · Morph=`γενηθῶμεν`

### Titus 3:8

- identicalFold: False
- TR tokens: 26 · Morph tokens: 24
- TR: πιστὸς ο λόγος καὶ περὶ τούτων βούλομαί σε διαβεβαιοῦσθαι ἵνα φροντιζωσιν καλῶν ἔργων προΐστασθαι οἱ πεπιστευκότες τῷ Θεῷ ταῦτά εστιν τὰ καλὰ καὶ ὠφέλιμα τοῖς ἀνθρώποις
- Morph: Πιστὸς ὁ λόγος καὶ περὶ τούτων βούλομαί σε διαβεβαιοῦσθαι ἵνα φροντίζωσιν καλῶν ἔργων προΐστασθαι οἱ πεπιστευκότες θεῷ ταῦτά ἐστιν καλὰ καὶ ὠφέλιμα τοῖς ἀνθρώποις

Ops:
- `tr_only`: TR=`τῷ` · Morph=``
- `tr_only`: TR=`τὰ` · Morph=``

### Titus 3:13

- identicalFold: False
- TR tokens: 11 · Morph tokens: 11
- TR: Ζηνᾶν τὸν νομικὸν καὶ Ἀπολλὼ σπουδαίως πρόπεμψον ἵνα μηδὲν αὐτοῖς λείπῃ
- Morph: ζηνᾶν τὸν νομικὸν καὶ Ἀπολλῶν σπουδαίως πρόπεμψον ἵνα μηδὲν αὐτοῖς λείπῃ

Ops:
- `substitute`: TR=`Ἀπολλὼ` · Morph=`Ἀπολλῶν`

### Titus 3:15

- identicalFold: False
- TR tokens: 18 · Morph tokens: 17
- TR: Ἀσπάζονταί σε οἱ μετ’ ἐμοῦ πάντες ἄσπασαι τοὺς φιλοῦντας ἡμᾶς ἐν πίστει η χάρις μετὰ πάντων ὑμῶν ἀμήν
- Morph: Ἀσπάζονταί σε οἱ μετ’ ἐμοῦ πάντες ἄσπασαι τοὺς φιλοῦντας ἡμᾶς ἐν πίστει ἡ χάρις μετὰ πάντων ὑμῶν

Ops:
- `tr_only`: TR=`ἀμήν` · Morph=``

## Phrase remap issues

_None._
