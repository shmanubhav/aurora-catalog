# Aurora spike results (cutoff 0.5)

**Verdict: Laya FAILS the frozen pass bar** (decision 1: at least 80% precision AND at least 80% recall AND finds reports rg missed). Precision 29.1%, weighted recall 76.3% (bootstrap upper bound 81.5%); it does find 22 sightings rg strict missed, so the "rg wins and the project stops" clause (zero finds) does not fire.

## Deviations from the locked design (all 2026-10-09, all user decisions)

- Adjudicator: Claude Opus, blind (same article text and rules a human would see), instead of the user (decision 3). Opus overturned 0 of 30 agreed checks; on the 30 real disagreements it sided with Claude (Sonnet) 18 times and with Gemma 12 times. Opus and Sonnet are one model family, so the answer key may lean slightly Sonnet's way.
- Gemma: moved from the M6 LM Studio QAT build to llm02 Ollama `gemma4:26b-a4b-it-mtp-q4_K_M` via the LiteLLM gateway; all 1,544 items relabeled there. On the 155 items both builds labeled: 150 same, 4 different, 1 llm02 loop.
- 8 Gemma reasoning loops (temperature 0 repetition, UNPARSED) went to adjudication as abstentions; Opus agreed with Claude on all 8.
- The cutoff sweep and any route split are post-hoc diagnostics. The verdict uses the frozen cutoff 0.5 only.

Labeled items: 1544 (pool 1229, net sample 315 at weight 5). Estimated positives in pool + loose net: 354 (pool 344, net sample 2 -> 10).

| | Flags | True | Precision (95% CI) | Weighted recall (95% bootstrap) |
|---|---|---|---|---|
| Laya >= 0.5 | 927 | 270 | 29.1% (26.3%-32.1%) | 76.3% (71.0%-81.5%) |
| rg strict | 584 | 322 | 55.1% (51.1%-59.1%) | 91.0% (86.5%-95.0%) |
| Either | | 344 | | 97.2% |

Laya-only sightings (rg strict missed): 22. rg-only sightings (Laya < 0.5): 74. Sightings missed by both (net sample): 2 sampled, about 10 estimated.

## Laya cutoff sweep (cutoffs below 0.5 are not measurable: lower-scored articles were only labeled when rg or the loose net flagged them)

| Cutoff | Flags | True | Precision | Weighted recall |
|---|---|---|---|---|
| 0.5 | 927 | 270 | 29.1% | 76.3% |
| 0.6 | 718 | 256 | 35.7% | 72.3% |
| 0.7 | 513 | 226 | 44.1% | 63.8% |
| 0.8 | 288 | 170 | 59.0% | 48.0% |
| 0.9 | 63 | 49 | 77.8% | 13.8% |

## Labelers
Claude vs Gemma: raw agreement 98.0%, Cohen's kappa 0.94 (1536 items; 8 Gemma loops excluded). Adjudicator overturned 0 of 30 agreed checks.

## Laya-only sightings

- line 116810 p=0.85 1859-09-17 Sugar planter. [volume] (West Baton Rouge [i.e. Port Allen, West Baton Rouge Parish, La.]) 1856-1925: Thar OPPOSITION 1lcKEr.-By refer   -ncr to another column, the proceed
- line 118333 p=0.84 1859-09-21 The Portage County Democrat. [volume] (Ravenna, Ohio) 1854-1868: the crimson prevailing entirely as it approach ed the horizon, and mos
- line 111293 p=0.84 1859-09-09 The Jeffersonian Democrat. [volume] (Chardon, Ohio) 1854-1865: The first Of these late phenomena, oc- Cured on Sunday evening the 26t
- line 77779 p=0.83 1859-09-24 Daily national Democrat.: A LETTER from Salt Lake says:
- line 67628 p=0.83 1859-09-07 Weekly standard. [volume] (Raleigh, N.C.) 1858-1865: ened his pace and gave him hobbling gait The. rude young man very unfe
- line 123437 p=0.81 1859-09-16 Wheeling daily intelligencer. [volume] (Wheeling, Va. [W. Va.]) 1852-1859: IL appears by late advices from the Pacific
- line 111460 p=0.79 1859-09-17 The Pacific commercial advertiser. [volume] (Honolulu, Hawaiian Islands) 1856-1888: THE PACIFIC Commercial Advertiser.  
- line 86817 p=0.76 1859-09-01 The Potter journal. [volume] (Coudersport, Pa.) 1857-1872: eenlium list again. The Orator for the / kcasion has not yet been engg
- line 62838 p=0.76 1859-09-16 The weekly pioneer and Democrat. [volume] (Saint Paul, Minn. Territory) 1855-1865: New York Letter.
- line 75687 p=0.75 1859-09-23 Richmond enquirer. [volume] (Richmond, Va.) 1815-1867: LETTER FROM NEW YORK.  I Correspondence Of the Hiehmo"d E"quIrer   Evu
- line 119507 p=0.75 1859-09-16 Evening star. [volume] (Washington, D.C.) 1854-1972: The ArRORA BOREAL!s IN ENGLAND The London News, of August 10Th. SAYS: 
- line 89021 p=0.72 1859-09-02 Ellsworth American. [volume] (Ellsworth, Me.) 1855-current: Our Beautiful Earth.
- line 86806 p=0.71 1859-09-01 The Potter journal. [volume] (Coudersport, Pa.) 1857-1872: While these changes we're taking place in the east and west, the wondr
- line 95492 p=0.70 1859-09-10 New-York daily tribune. [volume] (New-York [N.Y.]) 1842-1866: The NORTHERs LIGHT AT SEA.-Bsrk james w. Jones Paige, at this port fro
- line 139501 p=0.68 1859-09-08 Yorkville enquirer. [volume] (Yorkville, S.C.) 1855-2006: + once heard pretty good story Of one of those | men who oppose Agricu
- line 47182 p=0.61 1859-09-10 Keowee courier. [volume] (Pickens Court House, S.C.) 1849-current: Pennings and Clippings.
- line 144250 p=0.60 1859-08-29 Evening star. [volume] (Washington, D.C.) 1854-1972: vs,ted the attendance of the usual large congre- cations. and at sever
- line 152894 p=0.59 1859-09-01 Alexandria gazette. [volume] (Alexandria, D.C.) 1834-1974: The Atmospheric Phenomenon.
- line 130561 p=0.59 1859-09-23 The Hancock Jeffersonian. [volume] (Findlay, Ohio) 1857-1870: The Northern Lieb, n, Sea.
- line 99746 p=0.57 1859-09-15 Bradford reporter. [volume] (Towanda, Pa.) 1844-1884: RetDs from all Aattons.
- line 35305 p=0.56 1859-09-03 Dayton daily empire. [volume] (Dayton [Ohio]) 1850-1865: pThe Heavenly Lights" made their ap PeArance again last evening from h
- line 139527 p=0.54 1859-08-31 Dayton daily empire. [volume] (Dayton [Ohio]) 1850-1865: ExtraOrainarH Phenomena

## rg-only sightings Laya missed

- line 76551 p=0.02 1859-09-10 The Cecil Whig. [volume] (Elkton, Md.) 1841-current: GROVER g. BAKERS   CELEBRATED FAMILY SEWING MACHINES.
- line 74115 p=0.03 1859-09-17 Nashville union and American. [volume] (Nashville, Tenn.) 1853-1862: The Cotton Crop,
- line 119035 p=0.07 1859-09-06 The daily dispatch. [volume] (Richmond [Va.]) 1850-1884: AN OPP TINE TO SHOOT GAME-singul
- line 123061 p=0.07 1859-09-08 Holmes County Republican. [volume] (Millersburg, Holmes County, Ohio) 1856-1865: The LATE FRosTs.-Last week was re- markable for Borealis and Frosts. I
- line 48010 p=0.09 1859-09-01 The Alleghanian. [volume] (Ebensburg, Pa.) 1859-1865: E D T0RIAL kOTINGS
- line 107232 p=0.09 1859-08-29 The New York herald. [volume] (New York [N.Y.]) 1840-1920: r q s r. s o r I Pr.  MONDAY, 4 A. M.
- line 125095 p=0.12 1859-09-13 Daily Iowa State Democrat. [volume] (Davenport, Iowa) 1856-1859: M Jons ssss,sua, q Ds&se. psbliahss in II last Spirit Of ~ 1tns : shel
- line 109805 p=0.12 1859-09-05 The New York herald. [volume] (New York [N.Y.]) 1840-1920: REMARKH STRENGTHENING, cloudy; afterspon, clear Sunday-Mornng, cloudy;
- line 11796 p=0.13 1859-09-15 The New York herald. [volume] (New York [N.Y.]) 1840-1920: ADDITIONAL FROM EUROPE. ~<~>~ooocO~>~~->>orv>~~ Our Brussels, Florence
- line 141072 p=0.13 1859-09-06 The daily Gate City. [volume] (Keokuk, Iowa) 1855-1916: @Ws have lstsly had some very cold nights and mornings, and cool days,
- line 89858 p=0.13 1859-09-09 The daily dispatch. [volume] (Richmond [Va.]) 1850-1884: | NORTH CAROLINIANs IN TExAs-John H. | Manly, son of Ex-Goy. Manly, an
- line 12365 p=0.14 1859-09-29 The Wyandot pioneer. (Upper Sandusky, Ohio) 1853-1868: HAY Young lady aged about sixteen
- line 50464 p=0.14 1859-09-14 The eastern clarion. [volume] (Paulding, Miss.) 1837-1863: STARTLING ELECTRICAL PHENONENoN- This morning, one of the most startli
- line 14111 p=0.14 1859-09-05 Cleveland morning leader. [volume] (Cleveland [Ohio]) 1854-1865: Last week was remarkable for Borealis and Frosts. In some portions of 
- line 133780 p=0.14 1859-09-13 New Orleans daily crescent. [volume] ([New Orleans, La.]) 1851-1866: Hsh @rItans Bully Grsst.ut.
- line 145368 p=0.15 1859-09-22 Smyrna times.: BOsroN, April Is, 1852.
- line 152432 p=0.16 1859-09-05 Nashville patriot. [volume] (Nashville, Tenn.) 1858-1860: PIECE OF AURoRA BUREALIs I'VE learn m the New YORK Sun that Mr.. MERRI
- line 44863 p=0.16 1859-09-06 Alexandria gazette. [volume] (Alexandria, D.C.) 1834-1974: 80. Rorsalis and the Telegraph.
- line 147292 p=0.17 1859-09-23 Dayton daily empire. [volume] (Dayton [Ohio]) 1850-1865: gay-rhe Columbus Statesman says that young lady aged about sixteen, of
- line 99819 p=0.17 1859-09-09 The daily exchange. [volume] (Baltimore, Md.) 1858-1861: EXPERIMENTS DURING THE AUEoRA.-We were seat ed in the magnetic telegra
- line 103724 p=0.17 1859-09-08 Smyrna times.: FINE WRlfING.-rhe appearance Of an Aurora Boreals has Afforded newspap
- line 145061 p=0.17 1859-09-27 Dayton daily empire. [volume] (Dayton [Ohio]) 1850-1865: NEws ITEMs
- line 151439 p=0.18 1859-09-07 The daily dispatch. [volume] (Richmond [Va.]) 1850-1884: The income of Mr.. VIM Macdonald, the owner of Flora Temple, is said T
- line 52503 p=0.18 1859-09-20 Dayton daily empire. [volume] (Dayton [Ohio]) 1850-1865: NEWS ITEMS.
- line 67595 p=0.18 1859-09-21 Weekly standard. [volume] (Raleigh, N.C.) 1858-1865: The richness of her dress was only surpassed by   her beauty, which ne
- line 32803 p=0.18 1859-09-17 Semi-weekly standard. [volume] (Raleigh, N.C.) 1853-18??: The richness Of her drss vas soly sufpsssed BY   her beauty. which nee
- line 78567 p=0.18 1859-09-10 Nashville patriot. [volume] (Nashville, Tenn.) 1858-1860: The Cincinnati Price Current has the folio  The Aurora Boreaiis and th
- line 137759 p=0.18 1859-09-03 The New York herald. [volume] (New York [N.Y.]) 1840-1920: the GsIs% ba has on fseahlfrcm New Orleans 100000 Xgxican oulisTs   e 
- line 31310 p=0.18 1859-09-03 Alexandria gazette. [volume] (Alexandria, D.C.) 1834-1974: News Of the Day.  "To show the rery age and body Of the TINE.
- line 130424 p=0.19 1859-09-17 Keowee courier. [volume] (Pickens Court House, S.C.) 1849-current: CAMP MEETINGs.-The Camp Meeting at Center commences on Thursday before
- line 20407 p=0.19 1859-09-29 The Buchanan County guardian. (Independence, Buchanan County, Iowa) 1858-1864: The Aurora Borealis and the Telegraph
- line 138980 p=0.20 1859-09-01 The Iowa transcript. (Toledo, Tama County, Iowa) 1858-1866: Ihe 1o>pa transcript  AUGUST, 81, 1859.  Loo al News.
- line 111092 p=0.21 1859-09-03 The weekly hawk-eye. [volume] (Burlington, Iowa) 1858-1860: EARLY FRosT.-A gentleman residing at Ma per lille, Du Page county, abo
- line 96037 p=0.21 1859-09-06 Nashville patriot. [volume] (Nashville, Tenn.) 1858-1860: UNIvERsAL--It would seem that the recent aurora 6Oreahs was not gotten
- line 42477 p=0.21 1859-09-02 The New York herald. [volume] (New York [N.Y.]) 1840-1920: The News.
- line 138775 p=0.21 1859-09-28 The star of the north. [volume] (Bloomsburg, Pa.) 1849-1866: The AURORA BoREALIs AND THE TELEGRAPH. During the auroral display OH T
- line 46542 p=0.23 1859-09-28 New-York daily tribune.: | TIM C0mmeMOfetlVe vi &C cODg OF In Bel, to be presented to the birth
- line 75847 p=0.23 1859-09-07 Evening star. [volume] (Washington, D.C.) 1854-1972: THE EVENING STAR.
- line 80558 p=0.24 1859-09-28 New Orleans daily crescent. [volume] ([New Orleans, La.]) 1851-1866: INSANITY FROM FRIGHr.-The Columbus (Ohio) statesman says that young la
- line 34132 p=0.24 1859-09-14 The spirit of democracy. [volume] (Woodsfield, Ohio) 1844-1994: SHOOTING BY THE LIGHT OF THE AU- as it may appear, q gentleman actuall
- line 21102 p=0.24 1859-08-31 Worcester daily spy. [volume] (Worcester [Mass.]) 1850-1888: GENERAL NEWS SUMMARY  ESSEX COUNTY.
- line 148329 p=0.24 1859-09-12 The New York herald. [volume] (New York [N.Y.]) 1840-1920: The News.   By the arrival Of the steamer Ocean Queen of Cape Race on 
- line 82390 p=0.24 1859-09-13 Staunton spectator. [volume] (Staunton, Va.) 1849-1896: TIE AURORA BORBALIs AND THE TELEGRAPH. During the auroral display of T
- line 99258 p=0.25 1859-09-27 The daily dispatch. [volume] (Richmond [Va.]) 1850-1884: A., i y ECDA 4 GEPIEN   ISTxRxATrovAL CRICKET MArcH. s. The cricket ma
- line 37552 p=0.25 1859-09-01 The Evansville daily journal. [volume] (Evansville, Ia. [i.e. Ind.]) 1848-1862: ATur ArR6fs BoxgXIn. zlTbe SdOefiIJ
- line 124261 p=0.25 1859-09-03 Worcester daily spy. [volume] (Worcester [Mass.]) 1850-1888: GENERAL NEWS SUMMARY
- line 84309 p=0.26 1859-09-15 St. Cloud Democrat. [volume] (Saint Cloud, Stearns County, Minn.) 1858-1866: Frost! Frost! Jack Frost {!
- line 87789 p=0.26 1859-09-17 Keowee courier. [volume] (Pickens Court House, S.C.) 1849-current:    IsEMAKABIL PHENoMENA- recent aurora boreals was not only one of the
- line 96996 p=0.27 1859-09-30 The penny press. [volume] (Cincinnati [Ohio]) 1859-1860: NEWS AND GOSSIP.
- line 60885 p=0.27 1859-09-21 The penny press. [volume] (Cincinnati [Ohio]) 1859-1860: The Mechanics Institute.
- line 125190 p=0.28 1859-09-29 The penny press. [volume] (Cincinnati [Ohio]) 1859-1860: NEWS AND GOSSIP.
- line 95397 p=0.29 1859-09-30 The daily exchange. [volume] (Baltimore, Md.) 1858-1861: LATER FROM MEXIc0
- line 68398 p=0.29 1859-09-07 The Evansville daily journal. [volume] (Evansville, Ia. [i.e. Ind.]) 1848-1862: ExcIrED.-The Fort Wayne Times, in de- scribing the Aurora Borealis of 
- line 145562 p=0.30 1859-09-09 Richmond enquirer. [volume] (Richmond, Va.) 1815-1867: LETTER FROM NEW YORK.  : Cyrye,pgndence cf' Tic RicA1nona EAquirer. ] 
- line 70547 p=0.30 1859-08-30 The New York herald. [volume] (New York [N.Y.]) 1840-1920:    The Superintendent Of the Canadian Telegraph Compa- ny's lines sIt 
- line 78339 p=0.31 1859-08-30 Worcester daily spy. [volume] (Worcester [Mass.]) 1850-1888: From Boston.
- line 44183 p=0.32 1859-09-09 Delaware gazette. [volume] (Delaware, Ohio) 1855-1886: We have had frost several nights the pres ent week, but not of suffici
- line 13736 p=0.36 1859-09-01 The Buchanan County guardian. (Independence, Buchanan County, Iowa) 1858-1864: Aurora BOrealis.
- line 38197 p=0.36 1859-09-07 Alexandria gazette. [volume] (Alexandria, D.C.) 1834-1974: 1t is stated in the newspapers that in many parts of the country, the 
- line 115930 p=0.39 1859-09-15 Alexandria gazette. [volume] (Alexandria, D.C.) 1834-1974: 1t is said that many persons, during the late Auroral displays, fancie
- line 142464 p=0.41 1859-09-15 St. Cloud Democrat. [volume] (Saint Cloud, Stearns County, Minn.) 1858-1866: Frost Frost! Jack Frost I!
- line 22733 p=0.42 1859-09-07 The Louisiana Democrat. [volume] (Alexandria, La.) 1845-1918: NO WIRE-WORK,NG, :
- line 92279 p=0.42 1859-09-06 The daily dispatch. [volume] (Richmond [Va.]) 1850-1884: THn AuRoRA BoRKAtIs AND Tn1 TILE oRArH.-Dufing the auroral display on 
- line 77506 p=0.43 1859-09-02 Evening star. [volume] (Washington, D.C.) 1854-1972: TIE CENTRAL Gu2spH9ys.s71he prssen,   shell has been In use since tie 
- line 27678 p=0.43 1859-09-29 The national era. [volume] (Washington [D.C.]) 1847-1860: on the necessity of taking Gibraltar from the English, no matter by wh
- line 63417 p=0.44 1859-09-03 Alexandria gazette. [volume] (Alexandria, D.C.) 1834-1974: BY MAGNETIC TELEGRAPH.  The Aurora Borealis.
- line 45909 p=0.44 1859-08-30 The penny press. [volume] (Cincinnati [Ohio]) 1859-1860: River News.
- line 51762 p=0.44 1859-09-03 The Tipton advertiser. [volume] (Tipton, Cedar Co., Iowa) 1856-1962: The AURORA BoREALIs got up u -picndid exhibition on lsst Sunday nj gh,
- line 99801 p=0.45 1859-09-09 The daily exchange. [volume] (Baltimore, Md.) 1858-1861: | ! back at four O'Clock. He asked witness to leave ! draft that was a
- line 88522 p=0.45 1859-09-10 The penny press. [volume] (Cincinnati [Ohio]) 1859-1860: A SOUTHERN AuRoRAL DIspLAY.-The Nj
- line 81294 p=0.47 1859-09-09 The New York herald. [volume] (New York [N.Y.]) 1840-1920: WOOD. EDDY CO.. Wilmington Del. Whites Fall Style Gents Hats Now Rea- 
- line 79748 p=0.47 1859-09-23 The independent press. (Abbeville C.H., S.C.) 1853-1860:    lhs AuRoRS.-Fhe field Of observation The Aurora Borea'is, Of August
- line 47613 p=0.47 1859-09-10 Sugar planter. [volume] (West Baton Rouge [i.e. Port Allen, West Baton Rouge Parish, La.]) 1856-1925: ~ A contemporary says there should be harmony in the Democratic party 
- line 74036 p=0.50 1859-09-27 The daily exchange. [volume] (Baltimore, Md.) 1858-1861: BY THE OVERLAND MAIL-LATER FROM OR EGON AND WASHINGTON TERRITORY FUR  

## Sightings in the net sample (missed by both)

- line 115406 p=0.15 1859-09-14 The Nevada Democrat.: EARTHoUAoE IN MARIPosA CouNTY.-Thre, distinct shocks Of an earthquake 
- line 20393 p=0.12 1859-09-06 Richmond enquirer. [volume] (Richmond, Va.) 1815-1867: LETTER FROM PORTSMOUTH.

## Why rg missed Laya's 22 finds (read by a Sonnet agent, 2026-10-09)

- OCR-mangled keyword (11): e.g. "aurorcal display" (Kittanning, Pa.), "Northern Lighis" (Salt Lake), "Aur0ra Borea(tS", "northen lights" (Fairhaven, Mass.), "ArRORA BOREAL!s IN ENGLAND", "Northern Lieb, n, Sea", "No,tbe,n lights", "aurorial" (OCR slip or period spelling). An OCR-tolerant regex would likely catch most of these.
- Keyword-free description (9, 8 unique; 86806 and 152894 are the same New York Post text): "rainbow lights of the North" (New York); "some phenomenon in the heavens made it bright night. The sky was lurid" (Swannanoa valley to Salisbury, N.C.); "radiated like the spokes of a wheel from its hub" (Franconia Notch, N.H.); "moonless night could see the hands of my watch... one bright mellow light" (Chester District, S.C.); "The ruby crown... in the zenith" (New York Post); "The Heavenly Lights made their appearance again"; "red streaks of reflected light N. W." (Wayne); "white pure light shoot up like a sunbeam from the horizon to the zenith". This is Laya's real added value.
- Disputed (2): lines 89021 and 111460, the balloon Atlantic account (July flight, "phosphorescent atmosphere"); the reader judged these not aurora sightings although the answer key says YES. Left as labeled; it shows answer-key noise on ambiguous items. 95492 and 130561 are the same bark James W. Jones report at sea.
