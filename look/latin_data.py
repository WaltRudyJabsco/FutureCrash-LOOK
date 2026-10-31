"""Original LOOK concept checks, keyed to D'Ooge's lessons; no generated translations."""
# Number | question | correct | three distractors | explanation
CHECKS='''
0|What do macrons mark in this course?|Long vowels|Loud syllables|Silent letters|Plural nouns|A macron marks vowel length. Syllable weight and stress are related but distinct.
1|In 'puella poetam videt', who performs the action?|puella|poetam|videt|No subject is expressed|Puella is nominative and is the subject; poetam is accusative, the object.
2|Which case normally names the subject of a finite verb?|Nominative|Accusative|Genitive|Ablative|The nominative marks the subject. Latin endings often show roles without relying on word order.
3|Which case commonly expresses possession?|Genitive|Dative|Vocative|Accusative|The possessive genitive often corresponds to English 'of' or an apostrophe-s.
4|A finite verb agrees with its subject in which features?|Person and number|Case and gender|Declension and gender|Case and number|Subject-verb agreement concerns person and number, not the noun's declension.
5|Which case normally marks a direct object?|Accusative|Nominative|Genitive|Vocative|A transitive verb commonly takes its direct object in the accusative.
6|Which case commonly marks an indirect object?|Dative|Accusative|Vocative|Nominative|The dative commonly identifies the recipient: 'to' or 'for' someone.
7|What is the usual first-declension genitive singular ending?|-ae|-ī|-is|-ūs|The genitive singular identifies a noun's declension; the first declension has -ae.
8|An adjective agrees with its noun in what?|Gender, number and case|Declension only|Word order only|Person and tense|Agreement does not require noun and adjective to belong to the same declension.
9|Which second-declension ending commonly marks genitive singular?|-ī|-ae|-ēī|-um|The second-declension genitive singular is -ī.
10|What is true of neuter nouns?|Nominative and accusative have the same form|They never have plural forms|Their genitive is always -ae|They are all second declension|Neuters share nominative and accusative forms; neuter plural forms often end in -a.
11|Why is 'poēta bonus' masculine?|The adjective follows the noun's gender|Every -a noun is feminine|Bonus is a noun|Poēta is second declension|Poēta is a masculine first-declension noun. Bonus agrees in gender, number and case.
12|What is the familiar vocative singular of 'fīlius'?|fīlī|fīlie|fīlium|fīliōrum|Fīlius has the special vocative fīlī; the textbook also discusses contracted -ī genitives.
13|Which genitive belongs to 'ager'?|agrī|agerī|ageris|agrum|The stem is agr-. Not all -er nouns retain the e in oblique cases.
14|In 'mea puella', why is 'mea' feminine?|It agrees with the possessed noun|The speaker must be female|Mea is an adverb|Every possessive is feminine|A possessive adjective agrees with the thing possessed, not the possessor's gender.
15|How is personal accompaniment normally expressed?|cum plus ablative|cum plus genitive|Bare nominative|ad plus ablative|Personal accompaniment normally uses cum and the ablative; means usually uses a bare ablative.
16|What ending do the nine irregular adjectives share in genitive singular?|-īus|-ārum|-ibus|-am|The special genitive singular is -īus, with dative singular -ī.
17|Which form of 'is, ea, id' is neuter nominative singular?|id|ea|eum|eās|Is is masculine, ea feminine and id neuter in the nominative singular.
18|What does 'sum' mean?|I am|I shall be|I was|They are|Sum is present first-person singular. Eram is imperfect; erō is future.
19|Which infinitive identifies the second conjugation?|monēre|amāre|regere|audīre|The second conjugation has a long ē in the present active infinitive.
20|What does the imperfect commonly present?|An ongoing or repeated past action|Only a completed future action|A command|A future condition only|The imperfect often describes what was happening or used to happen.
21|Which form means 'I shall love'?|amābō|amābam|amāvī|amō|First- and second-conjugation futures use -bō, -bis, -bit and related endings.
22|Which case follows 'amīcus' when it means 'friendly to'?|Dative|Vocative|Accusative|Nominative|Certain adjectives take a dative complement; do not translate English 'to' mechanically as ad.
23|Which form means 'they rule'?|regunt|regent|reguntur|rēxērunt|Regunt is present active; regent is future; reguntur is passive.
24|Which is the imperfect of 'audiō', first-person singular?|audiēbam|audībō|audīvī|audiam|The fourth conjugation uses audiēbam in the imperfect.
25|Which form means 'I shall rule'?|regam|regō|regēbam|rēxeram|The third-conjugation future begins regam, regēs, reget.
26|Which is a singular active imperative of 'amō'?|amā|amō|amās|amābō|Amā commands one person; amāte commands more than one.
27|What changes in a passive sentence?|The subject receives the action|The verb loses person|Every noun becomes ablative|The subject must be absent|Passive voice changes the subject's relation to the action; it does not remove agreement.
28|What does 'reguntur' mean?|They are ruled|They rule|They will rule|They had ruled|The -ntur ending marks third-person plural passive.
29|Which is the present passive infinitive of 'regō'?|regī|regere|rēxisse|rēctum esse|Third-conjugation present passive infinitives end in -ī.
30|How is a personal agent normally expressed with a passive verb?|ā or ab plus ablative|ad plus accusative|Bare vocative|in plus genitive|Use ā/ab with the ablative for the personal agent; distinguish agent from instrument.
31|Which form of 'sum' means 'I had been'?|fueram|fuī|eram|fuero|Fueram is pluperfect; fuī is perfect and eram imperfect.
32|Which principal part supplies the perfect active stem?|The third principal part|The present infinitive alone|The perfect passive participle|The noun's genitive|Remove -ī from the third principal part: amāvī gives the perfect stem amāv-.
33|What does 'amāveram' mean?|I had loved|I shall love|I was loving|I am loved|The pluperfect places an action before another past point.
34|Which form is future perfect active?|amāverō|amābō|amāveram|amābam|Amāverō means 'I shall have loved'; amābō is simple future.
35|How is the perfect passive built?|Perfect passive participle plus present of sum|Present stem plus -bam|Perfect stem plus -ī|Infinitive plus -mus|Amātus sum is masculine singular; the participle agrees with the subject.
36|What does enclitic '-ne' commonly do?|Marks a yes-or-no question|Makes every verb negative|Creates a plural noun|Marks a superlative|Attach -ne to a word, often the first, to introduce a direct question.
37|What does 'possum' mean?|I am able|I carry|I go|I become|Possum is formed historically from pot- and sum; it commonly takes an infinitive.
38|What determines a relative pronoun's case?|Its job in its own clause|The antecedent's case automatically|Its position in the sentence|The main verb's person|It agrees with the antecedent in gender and number; its own clause determines case.
39|Which case is essential for finding a third-declension noun's stem?|Genitive singular|Nominative plural only|Vocative singular only|Accusative plural only|Remove -is from the genitive singular to find the base used in many forms.
40|What is the base of 'rēx, rēgis'?|rēg-|rēx-|rēgi-|rēge-|The genitive rēgis reveals the base rēg-.
41|What is the neuter plural of 'corpus'?|corpora|corpī|corporēs|corporūs|Corpus, corporis has neuter plural corpora.
42|Which pair can have different declensions but still agree?|poēta bonus|puella bonum|bellum bona|rēx bonam|Poēta is first declension and bonus second; both are masculine nominative singular.
43|What genitive plural ending characterizes third-declension i-stems?|-ium|-ōrum|-ārum|-uum|The i-stem genitive plural is -ium; the full rules have exceptions and subgroups.
44|Why learn gender with a noun?|Endings alone do not always determine it|All third-declension nouns are neuter|Gender changes every tense|Only adjectives have gender|Dictionary entries give gender because general patterns have exceptions.
45|What is the usual ablative singular ending of an i-stem adjective?|-ī|-am|-ōrum|-ūs|Third-declension adjectives such as fortis commonly have ablative singular fortī.
46|What is the fourth-declension genitive singular ending?|-ūs|-us with short u only|-is|-ēī|Macrons distinguish the genitive -ūs from forms with a short u.
47|What does the locative commonly express?|Place where|Personal agent|Direct object|Future time only|Names of towns, small islands and a few nouns preserve special place constructions.
48|What is the fifth-declension genitive singular of 'rēs'?|reī|rēs|rērum|rēbus|Rēs has genitive singular reī; diēs has diēī.
49|What does the reflexive pronoun normally refer back to?|The relevant clause's subject|Any nearby noun at random|Only the speaker|Only a plural antecedent|Reflexive reference is tied to the subject; indirect discourse needs additional care.
50|What does 'ipse' add?|Emphasis: self or very|Automatic reflexive possession|A future tense|A negative meaning|Ipse is intensive; do not confuse intensive and reflexive functions.
51|Which demonstrative commonly means 'this' near the speaker?|hic|ille|iste|nēmō|Hic commonly points to what is near the speaker; context can add further contrasts.
52|What does 'aliquis' commonly mean?|Someone or something|No one|Everyone without exception|The same person|Aliquis is indefinite. After sī, nisi, nē and num, simple quis often has indefinite force.
53|What is the regular comparative suffix?|-ior, neuter -ius|-issimus only|-bilis|-mentum|Comparatives decline as third-declension adjectives: fortior, fortius.
54|Which case can replace 'quam' after a comparative?|Ablative|Vocative|Genitive in every context|Nominative in every context|The ablative of comparison is an alternative in appropriate constructions.
55|What is the neuter comparative corresponding to 'multus'?|plūs|maximē|maius|melius|Multus, plūs, plūrimus is irregular; plūs has its own inflection.
56|In a comparison, what can a measure-of-difference ablative express?|How much more or less|Who is being addressed|The sentence's direct object|A yes-or-no question|Multō maior means 'much greater': multō measures the difference.
57|What is the regular comparative of the adverb 'clārē'?|clārius|clārior|clārissimus|clārī|The comparative adverb uses the neuter accusative singular of the comparative adjective.
58|Which case commonly expresses a whole after a word for a part?|Genitive|Vocative|Accusative only|Nominative only|A partitive genitive specifies the whole from which a part is taken.
59|Which case commonly expresses duration or extent?|Accusative|Vocative|Genitive only|Dative only|An accusative can express how long or how far; distinguish time when in the ablative.
60|What is a deponent verb?|Passive in form, active in meaning|Active in form, always passive in meaning|A verb with no principal parts|A noun used as a verb|Deponents use passive forms with active meanings and require their own principal parts.
61|What is the subjunctive?|A mood used in several independent and subordinate constructions|A fourth time period|A noun declension|A passive-only voice|Mood is not tense. The subjunctive has multiple uses, not a single English equivalent.
62|What introduces a positive purpose clause?|ut plus subjunctive|ut plus future indicative only|nē plus indicative|cum plus infinitive only|A purpose clause commonly uses ut; a negative purpose uses nē.
63|How is the imperfect subjunctive active formed?|Present active infinitive plus personal endings|Perfect participle plus erō|Present stem plus -bō|Genitive stem plus -is|Amāre gives amārem. Vowel length changes appear in several persons.
64|Which tense expresses a completed action before a secondary-sequence subjunctive context?|Pluperfect subjunctive|Future indicative|Present imperative|Future perfect indicative always|In normal secondary sequence, anterior action is expressed by the pluperfect subjunctive.
65|After a verb of fearing, what does 'nē' commonly introduce?|The event feared might happen|An ordinary direct command|A relative antecedent|A noun's gender|Timeō nē veniat means 'I fear that he may come'; fearing clauses differ from ordinary purpose clauses.
66|What does a Latin participle combine?|Verbal meaning and adjectival agreement|Only noun possession|Only adverb comparison|No relationship to a noun|A participle can take verbal complements while agreeing with a noun in gender, number and case.
67|What forms the usual ablative absolute?|A noun or pronoun and a participle in the ablative|An accusative subject plus infinitive|A dative plus future indicative|A vocative plus imperative only|The construction is grammatically detached from the main clause; some absolutes use a noun or adjective predicate.
68|How is a negative result clause commonly expressed?|ut nōn plus subjunctive|nē plus imperative|nōnne plus infinitive|sine plus indicative|Purpose commonly negates with nē; result commonly uses ut nōn.
69|What does a relative clause of characteristic describe?|The sort of person or thing involved|Only an exact clock time|Only a direct quotation|A compulsory command|The subjunctive can characterize a type rather than merely identify a specific fact.
70|What is common in a circumstantial 'cum' clause referring to the past?|Subjunctive mood|Imperative mood|Future infinitive only|No verb|Cum with a subjunctive often supplies background circumstance, cause or concession; not every cum clause uses it.
71|What is a gerundive?|A verbal adjective|A finite perfect verb|An indeclinable conjunction|A comparative adverb|A gerundive agrees with a noun; in the passive periphrastic it can express necessity or obligation.
72|What is the usual structure of an indirect statement after a verb of saying?|Accusative subject and infinitive|Nominative subject and imperative|Vocative and gerund only|Dative and future indicative|The infinitive's tense is relative to the reporting verb, not simply to the present moment.
73|What is the present active infinitive of 'ferō'?|ferre|ferere|tulisse|lātum esse|Ferō, ferre, tulī, lātus is irregular; tulisse is perfect active.
74|What mood is normally used in an indirect question?|Subjunctive|Imperative|Indicative in every case|Infinitive in every case|An indirect question uses the subjunctive and follows the appropriate tense relationships.
75|In 'auxiliō venit', what can 'auxiliō' express?|Purpose: he comes as a help|A direct object|The person addressed|A completed past passive|A dative of purpose states the service or end for which something is done.
76|Which cases can express quality with suitable modifiers?|Genitive and ablative|Vocative and nominative only|Accusative only|Locative only|Both the genitive and ablative can describe a quality; modifiers and usage matter.
77|A predicate adjective agrees with its subject in what?|Gender, number and case|Person and conjugation|Only its final letter|Only word order|Predicate adjectives agree with the subject noun; noun predicates have different gender behavior.
78|Which is normally a bare ablative rather than 'cum' plus ablative?|An instrument or means|A personal companion|A direct object|A person addressed|Gladiō can mean 'with a sword' as an instrument; a personal companion normally takes cum.
79|In 'liber legendus est', what does the construction commonly express?|The book must be read|The book has just read|The book will certainly write|The book is a comparative|The passive periphrastic joins a gerundive with sum to express obligation or necessity.
'''

# Textbook forms. Alternatives are separated by / and accepted as equivalent.
NOUNS=[
 ('puella',7,'puella puellae puellae puellam puellā puella','puellae puellārum puellīs puellās puellīs puellae'),
 ('servus',9,'servus servī servō servum servō serve','servī servōrum servīs servōs servīs servī'),
 ('bellum',10,'bellum bellī bellō bellum bellō bellum','bella bellōrum bellīs bella bellīs bella'),
 ('rēx',39,'rēx rēgis rēgī rēgem rēge rēx','rēgēs rēgum rēgibus rēgēs rēgibus rēgēs'),
 ('corpus',41,'corpus corporis corporī corpus corpore corpus','corpora corporum corporibus corpora corporibus corpora'),
 ('cīvis',43,'cīvis cīvis cīvī cīvem cīve cīvis','cīvēs cīvium cīvibus cīvēs/cīvīs cīvibus cīvēs'),
 ('mare',43,'mare maris marī mare marī mare','maria marium maribus maria maribus maria'),
 ('manus',46,'manus manūs manuī manum manū manus','manūs manuum manibus manūs manibus manūs'),
 ('diēs',48,'diēs diēī diēī diem diē diēs','diēs diērum diēbus diēs diēbus diēs'),
]
VERBS=[
 ('amō',19,'amāre','amā','amāv','am','amō amās amat amāmus amātis amant','amor amāris/amāre amātur amāmur amāminī amantur'),
 ('moneō',19,'monēre','monē','monu','mone','moneō monēs monet monēmus monētis monent','moneor monēris/monēre monētur monēmur monēminī monentur'),
 ('regō',23,'regere','reg','rēx','reg','regō regis regit regimus regitis regunt','regor regeris/regere regitur regimur regiminī reguntur'),
 ('audiō',23,'audīre','audi','audīv','audi','audiō audīs audit audīmus audītis audiunt','audior audīris/audīre audītur audīmur audīminī audiuntur'),
 ('capiō',26,'capere','capi','cēp','capi','capiō capis capit capimus capitis capiunt','capior caperis/capere capitur capimur capiminī capiuntur'),
]
