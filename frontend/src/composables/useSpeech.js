/**
 * Web Speech API 封装（TTS 降级方案 + 分角色朗读）。
 * 根据说话人性别从浏览器英文声源中匹配对应音色。
 * 角色性别由后端 video_clips.character_genders 提供。
 */

// ── 名字→性别映射（覆盖 Microsoft / Google / Amazon 等声源） ──
const MALE_NAMES = new Set([
  // Microsoft Chinese TTS voices
  'kangkang','yunyang','yunxi','xiaomo',
  // English voices
  'david','mark','william','richard','james','john','robert','michael','thomas',
  'christopher','daniel','paul','andrew','steven','joseph','george','kenneth',
  'edward','brian','kevin','ronald','timothy','jason','jeffrey','ryan','jacob',
  'gary','nicholas','eric','stephen','jonathan','larry','justin','scott','brandon',
  'benjamin','samuel','raymond','gregory','frank','alexander','patrick','jack',
  'dennis','jerry','tyler','aaron','jose','nathan','henry','douglas','peter',
  'adam','nathaniel','zachary','charles','donald','steve','matthew','luke',
  'anthony','gabriel','julian','miguel','sean','oscar','vicente','raul','ricardo',
  'jorge','fernando','roberto','carlos','antonio','javier','manuel','alejandro',
  'santiago','diego','eduardo','enrique','pedro','francisco','alberto','arturo',
  'ramon','mario','juan','luis','josef','ernesto','guillermo','hector','ruben',
  'gerardo','alfredo','felipe','marco','ismael','hormazd','neil','simon','harry',
  'liam','noah','oliver','elijah','henry','lucas','ezekiel','levi',
  'sebastian','dylan','grayson','carter','wyatt','owen','jaxon','ezra','silas',
  'miles','ian','brooks','declan','harrison','wesley','jameson','tucker','maxwell',
  'asher','thomas','sam','joshua','cameron','connor','evan','nolan',
  'chase','cole','cooper','hayden','jordan','landon','micah','ryder','xavier',
  'stefan','stephan','steffan','brandan','brendan','brent','bryce','byron',
  'caleb','clayton','clifford','clint','colby','colin','collin','conner','cory',
  'dakota','dallas','damian','damien','damon','dandre','darin','darnell','darrel',
  'darrell','darren','darrin','darryl','daryl','dave','davian','davion','davis',
  'dawson','dax','dayton','deandre','deangelo','declan','demarcus','demetrius',
  'deon','devan','devin','dewayne','dewey','dexter','dillon','dimitri','dirk',
  'dominick','dominique','don','donavan','donnell','donnie','donny','donovan',
  'dorian','dorman','doug','drew','duncan','dustin','dwayne','dwight',
  'earl','efrain','efren','elbert','eldon','eldridge','eli','elias','eliezer',
  'elijah','eliseo','elisha','elliot','elliott','ellis','ellsworth','elmer',
  'elmo','elvin','elvis','emanuel','emerson','emery','emil','emilio','emmanuel',
  'emmett','emmitt','emory','erik','ernest','ernesto','errol','erwin','esteban',
  'estevan','ethan','eugene','evan','everett','ezekiel','ezra','fidel','filiberto',
  'floyd','forest','forrest','foster','franklin','fred','freddie','freddy',
  'frederic','frederick','fredric','fritz','geoffrey','gerald','gerard','gerardo',
  'german','gerrod','giovanni','giuseppe','glen','glenn','gonzalo','gordon',
  'grady','graham','grant','greg','gregg','gregorio','gregory','guillermo','gus',
  'gustavo','hakeem','hakim','hal','hank','hans','hardy','harley','harmon',
  'harold','harper','harris','harrison','harry','harvey','hassan',
  'heath','hector','henry','herbert','herman','herminio','hilton','hipolito',
  'hiram','hirsch','homer','horace','horatio','hosea','houston','howard','hubert',
  'huey','hugh','hugo','humberto','hung','hunter','hyman','ian','ignacio',
  'ike','immanuel','irvin','irving','irwin','isaac','isaiah','isaias','ishmael',
  'isidro','ismael','israel','isreal','issac','ivan','ivory','jack','jackie',
  'jackson','jacob','jacques','jade','jake','jalen','jamal','jamar','jamel',
  'james','jamey','jamie','jamil','jamison','jan','jared','jarod','jarred',
  'jarrett','jarrod','jarvis','jason','jasper','javier','jay','jayce','jaycee',
  'jayden','jaydon','jaymes','jaylen','jayson','jean','jed','jedediah','jeff',
  'jefferey','jefferson','jeffery','jeffrey','jeffry','jemal','jenkins','jensen',
  'jerald','jeramy','jerel','jereme','jeremiah','jeremie','jeremy','jermaine',
  'jermey','jerod','jerome','jeromy','jerrell','jerrod','jerry','jess','jesse',
  'jessey','jessie','jesus','jim','jimmie','jimmy','joe','joel','joesph','joey',
  'johnathan','johnathon','johnie','johnnie','johnny','johnson','jon','jonah',
  'jonas','jonatan','jonathon','jonny','jorden','jordon','jordy','jorge','jose',
  'josef','joseph','josh','joshua','josiah','josue','juan','judah','judd','jude',
  'judson','jules','julian','julio','julius','junior','justin','kade','kaleb',
  'kaleo','kamden','kameron','kamron','kane','kareem','karl','karson','kasey',
  'kasper','keenan','keith','kellen','kelley','kelly','kelton','kelvin','ken',
  'kendall','kendrick','kenji','kennedy','kenneth','kennith','kenny','kent',
  'kenton','kenyatta','kermit','kerry','kevan','keven','kevin','keyon','keyshawn',
  'khalid','khalil','kiel','kip','kipling','kirby','kirk','kirsten','kasey','kit',
  'kody','kole','kolton','korey','kory','kraig','kris','kristian','kristofer',
  'kristoffer','kristopher','kurt','kurtis','kwame','kyle','kylee','kyler',
  'kylen','kyson','lamar','lambert','lamont','lance','landan','landen','landon',
  'landry','lane','langston','lanny','larry','laurence','lawerence','lawrence',
  'layne','lazaro','leandro','lee','leif','leland','lemuel','len','lenard',
  'lennie','lennon','lennox','leo','leon','leonard','leonardo','leonel','leopold',
  'leroy','les','lesley','leslie','lessie','lester','levi','levin','lewis',
  'lia','lincoln','lindsay','lindsey','linwood','lionel','lisandro','lloyd',
  'logan','london','lonnie','lonny','loren','lorenzo','lou','louie','louis',
  'lowell','loyd','lucas','luciano','lucius','luigi','luis','luke','luther',
  'lyle','lyndon','lynn','lyle','mack','major','malachi','malcolm','marcos',
  'marcus','marion','mariano','mario','mark','markel','markell','markus',
  'marlin','marlon','marques','marquez','marquis','marquise','marshall','martin',
  'marty','marvin','mason','mateo','mathew','matias','matt','matteo','matthew',
  'maurice','mauricio','max','maxim','maxime','maximilian','maximiliano','maxwell',
  'maxx','mckenna','mckinley','mclean','mead','mehtab','mel','melvin','melvyn',
  'michael','michal','michale','micheal','michel','miguel','mike','mikel',
  'mikhail','miles','milford','millard','milo','milton','mitch','mitchel',
  'mitchell','moises','monroe','monte','montgomery','monty','morgan','morris',
  'morton','mose','moshe','moses','muhammad','murray','mustafa','mychal',
  'myles','myron','nathanael','nathanial','neal','neil','nelson','nestor',
  'neville','newton','nicholas','nick','nicklaus','nickolas','nicky','nicolas',
  'nigel','niki','nikko','nikolai','nikolas','nil','niles','noah',
  'noe','noel','nolan','norbert','norman','normand','norris','numbers','obed',
  'octavio','odon','olaf','olen','olin','oliver','ollie','omar','omer','oren',
  'orion','orlando','orrin','orville','osbaldo','osborne','oscar','osvaldo',
  'oswaldo','otis','otto','owen','pablo','pace','paco','paris','parker',
  'parry','pasquale','pat','patric','patrick','paul','paulo','pedro','pele',
  'percy','perry','pete','peter','peyton','phil','philip','phillip','phillipe',
  'philip','pierre','porter','preston','prince','quentin','quinn','quinten',
  'quintin','quinton','rafael','raheem','rahim','raleigh','ralph','ramiro',
  'ramon','ramses','randal','randall','randell','randolph','randy','raphael',
  'rashad','rashawn','raul','ray','rayford','raymond','raymundo','reed','reese',
  'reginald','reid','reilly','remington','remy','renato','rene','rey','reye',
  'reynaldo','rhett','rhys','ricardo','ricci','rich','richard','richie','rick',
  'rickey','rickie','ricky','rico','rigoberto','riley','rob','robb','robbie',
  'robby','robert','roberto','robin','rocco','rock','rocky','rod','rodey',
  'rodger','rodney','rodolfo','rodrick','rodrigo','rogelio','roger','rohan',
  'roland','rolando','rolf','rolland','roman','romeo','ron','ronald','ronnie',
  'ronny','roosevelt','rory','roscoe','ross','roy','royce',
  'ruben','rudolph','rudy','rufus','rupert','russ','russel','russell','rusty',
  'ryan','ryder','ryland','sal','salvador','salvatore','sam','sammie','sammy',
  'samson','samual','samuel','sander','sanders','sandor','sandy','sanford',
  'sang','santiago','santo','santos','saul','saunders','scot','scott','scottie',
  'scotty','sean','sebastian','seymour','shad','shane','shannon','shaquille',
  'shayne','shea','shedrick','sheldon','shelton','sherman','shirley','shon',
  'shuan','sid','sidney','sigurd','silas','silvester','simeon','simon','sky',
  'skye','skyler','slade','sloan','solomon','sonny','spencer','stan','stanford',
  'stanley','stanton','stefan','stefano','stephan','stephen','stevan','steve',
  'steven','stevie','stewart','stuart','sullivan','sumner','sydney','tad',
  'talbot','talon','tanner','tate','taylor','teagan','ted','teddy','terance',
  'terell','terence','terrance','terrell','terrence','terrill','terry','tevin',
  'thad','thaddeus','theo','theodore','theron','thomas','thompson','thor',
  'thorton','tim','timmie','timmy','timothy','tito','titus','tobias','tobie',
  'tobin','toby','tod','todd','tom','tomas','tommie','tommy','tony','torey',
  'torrance','torrey','tracy','trae','tran','trant','travis','travon','tre',
  'tremaine','tremayne','trent','trenten','trenton','trever','trevion','trevor',
  'trey','trinidad','trinity','tristan','tristen','tristian','triston','troy',
  'truman','tucker','ty','tye','tyler','tymon','tymothy','tyree','tyrel',
  'tyrell','tyron','tyrone','tyshawn','tyson','ulises','ulysses','uriah',
  'uriel','val','valentin','valentine','van','vance','vaughn','vern','vernon',
  'vicente','victor','vince','vincent','vincenzo','virgil','virgilio','vito',
  'von','wade','wagner','walker','wallace','wally','walter','walton','ward',
  'warner','warren','waylon','wayne','wei','welker','wendell','werner','wes',
  'wesley','westin','weston','whitney','wilber','wilbert','wilbur','wiley',
  'wilford','wilfred','wilfredo','wilhelm','will','willard','william','willie',
  'willis','willy','wilmer','wilson','wilton','winfield','winfred','winston',
  'woodrow','wyatt','xander','xavier','xia','xiao','xu','yahir','yair','yale',
  'yardley','yehuda','yisrael','yosef','yoshio','young','yu','yuri','zach',
  'zachariah','zachary','zachery','zack','zackary','zackery','zaire','zane',
  'zavier','zeb','zebadiah','zebediah','zebulun','zeke','zeller','zeph','zeth',
  'zollie','zolly','zoran','zulkifli'
])

const FEMALE_NAMES = new Set([
  // Microsoft Chinese TTS voices
  'huihui','yaoyao','zhiyu','xiaoxiao',
  // English voices
  'zira','hazel','jenny','susan','catherine','helena','lisa','karen','nancy',
  'betty','helen','donna','carol','sandra','ruth','patricia','barbara','linda',
  'mary','margaret','dorothy','gloria','evelyn','lucy','anna','emma','sophia',
  'olivia','isabella','mia','charlotte','amelia','harper','abigail','emily',
  'elizabeth','avery','sofia','chloe','ellie','stella','zoey','nora','lily',
  'violet','aubrey','scarlett','hannah','audrey','skyler','leah','kaylee',
  'piper','sarah','madelyn','brooklyn','peyton','katherine','addison','layla',
  'savannah','ava','hailey','jessica','ashley','amanda','jennifer','stephanie',
  'nicole','amber','brittany','danielle','victoria','rachel','christina',
  'lauren','kelly','heather','tiffany','michelle','kristen','amy','rebecca',
  'tina','crystal','alison','cynthia','andrea','kimberly','april','tammy',
  'laura','erin','wendy','janice','anne','gina','julia','kathleen','joan',
  'maria','elena','eva','clara','cora','iris','rose','daisy','ruby','jade',
  'luna','eden','celeste','alice','grace','chloe','penelope','aria','elliana',
  'hana','noa','sara','maya','naomi','gabrielle','isabel','eleanor','annabelle',
  'brielle','carly','jordyn','kendall','morgan','reese','paige','mackenzie',
  'molly','kate','julia','rachel','allison','alexandra','brooklyn','kaitlyn',
  'megan','samantha','sydney','taylor','autumn','faith','hope','ashlyn',
  'mikayla','brianna','trinity','jasmine','makayla','kylie','mckenzie','kaitlin',
  'kimber','alexis','katelyn','cheyenne','kayla','sierra','cassandra','breanna',
  'alexa','jacqueline','kristina','hayley','marissa','karina','mary','jacquelyn',
  'cristina','courtney','tara','jill','erica','lindsay','janelle','holly',
  'caitlin','caitlyn','jade','bridget','rachael','jocelyn','rebekah','whitney',
  'brittney','meredith','brenda','leslie','shannon','heidi','candice','yvonne',
  'constance','shelly','kellie','jana','carrie','stacey','krista','renee',
  'janna','rome','tamara','melanie','natalie','kelsey','maribel','cierra',
  'kiana','jessika','kaci','nikki','brandy','johanna','kristin','tricia',
  'janae','nikita','britney','kortney','myra','deann','chantel','brandi',
  'michaela','diana','martha','bev','cynthia','rebecca','bridgette',
  'alisha','latoya','gwendolyn','veronica','jeanette','kristie','juliana',
  'allyson','cathryn','priscilla','lizbeth','robin','evette','emilia',
  'kaleigh','moriah','shayna','shana','deana','juliet','meaghan','eve',
  'giselle','noelle','deann','annmarie','kathrine','constance','patrice',
  'raquel','cleo','zoey','macy','desiree','gisela','liyah','katrina',
  'rosemary','clare','isobel','roxanne','elise','alaina','shelby','jodie',
  'nacole','kristan','pamela','selina','deborah','lynette','josie','debra',
  'amberly','rosalind','chelsey','camilla','myra','annette','annalee',
  'alina','tiara','beverly','darlene','genevieve','jewel','tia','kaitlynn',
  'tomiko','maggie','tabitha','lucille','evangelina','erika','jody','tianna',
  'marguerite','mollie','lucia','bryanna','kristyn','chaya','alissa',
  'sharon','rhonda','regina','monique','earline','bridgette','fawn','cassie',
  'darcy','leona','dorthy','miriam','sharlene','joelle','efigenia','lavon',
  'emilee','cori','melva','lloyd','carolina','susanna','rosie','leola',
  'sandy','noreen','latonya','carlee','caitlynn','patsy','summer',
  'theresa','caroline','sonia','kathryn','belinda','alia','sherri',
  'cristal','nadia','celina','bridgett','rayna','trisha','kaitlin',
  'latoya','larissa','johana','darline','sheryl','sheila','terri'
])

const _voiceList = [];
let _voicesLoaded = false;
let _lastVoice = null;

/** 从声源全名中提取名字部分 */
function extractFirstName(voiceName) {
  let name = voiceName.toLowerCase()
    .replace(/^microsoft\s*/i, '')
    .replace(/\s*online\s*\(natural\)\s*/i, '')
    .replace(/\s*multilingual\s*/i, '')
    .replace(/\s*\(.*?\)\s*/g, ' ')
    .replace(/\s*-.*$/, '')
    .replace(/google\s*/i, '')
    .trim();
  return name.split(/\s+/)[0] || '';
}

/** 判断声源性别 */
function guessVoiceGender(voice) {
  const name = extractFirstName(voice.name);
  if (MALE_NAMES.has(name)) return 'male';
  if (FEMALE_NAMES.has(name)) return 'female';
  // 特殊字符串匹配兜底（中英文）
  const lower = voice.name.toLowerCase();
  if (lower.includes('female') || lower.includes('girl')) return 'female';
  if (lower.includes('male') || lower.includes('boy')) return 'male';
  // Chinese voice keywords
  if (lower.includes('huihui') || lower.includes('yaoyao') || lower.includes('zhiyu') || lower.includes('xiaoxiao')) return 'female';
  if (lower.includes('kangkang') || lower.includes('yunyang') || lower.includes('yunxi') || lower.includes('xiaomo')) return 'male';
  return 'unknown';
}

/** 加载 TTS 声源列表，返回英文声源数组 */
function loadVoices() {
  if (_voicesLoaded && _voiceList.length > 0) return Promise.resolve(_voiceList);

  const immediate = window.speechSynthesis.getVoices();
  if (immediate.length > 0) {
    _voiceList.push(...immediate);
    _voicesLoaded = true;
    return Promise.resolve(_voiceList);
  }

  return new Promise(resolve => {
    window.speechSynthesis.onvoiceschanged = () => {
      const v = window.speechSynthesis.getVoices();
      if (v.length > 0) {
        _voiceList.push(...v);
        _voicesLoaded = true;
        window.speechSynthesis.onvoiceschanged = null;
        resolve(_voiceList);
      }
    };
    // 超时兜底
    let tries = 0;
    const iv = setInterval(() => {
      tries++;
      const v = window.speechSynthesis.getVoices();
      if (v.length > 0) {
        _voiceList.push(...v);
        _voicesLoaded = true;
        window.speechSynthesis.onvoiceschanged = null;
        clearInterval(iv);
        resolve(_voiceList);
      }
      if (tries > 25) { clearInterval(iv); resolve(_voiceList); }
    }, 200);
  });
}

/** 筛选英文声源 */
function _enVoices() {
  return _voiceList.filter(v => v.lang.startsWith('en'));
}

/** 按性别返回可用的声源列表（优先英文，兜底全部） */
function voicesByGender(gender) {
  const en = _enVoices().filter(v => guessVoiceGender(v) === gender);
  if (en.length > 0) return en;
  // 没有英文声源时在所有声源中按性别筛选
  return _voiceList.filter(v => guessVoiceGender(v) === gender);
}

/**
 * 选取指定性别的声源，优先选择与上一次不同的声源（避免连续同角色用同一个音色）。
 * @param {'male'|'female'} gender
 * @returns {SpeechSynthesisVoice|null}
 */
function pickVoice(gender) {
  const candidates = voicesByGender(gender);
  if (candidates.length === 0) return null;

  // 优先选一个与上次不同的
  const different = candidates.find(v => v.name !== _lastVoice?.name);
  const chosen = different || candidates[0];
  _lastVoice = chosen;
  return chosen;
}

/**
 * 朗读单句文本。
 * @param {string} text
 * @param {'male'|'female'} gender
 * @param {string} lang
 * @param {number} rate
 */
async function speakText(text, gender = "female", lang = "en-US", rate = 0.85) {
  if (!window.speechSynthesis) return;
  try { await loadVoices(); } catch { /* 静默降级 */ }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.rate = rate;

  const voice = pickVoice(gender);
  if (voice) utterance.voice = voice;

  window.speechSynthesis.speak(utterance);
}

/**
 * 分角色朗读对话（自动切换男女声）。
 * @param {Array<{speaker: string, text: string, gender: string}>} dialogues
 * @param {number} rate
 */
async function speakDialogues(dialogues, rate = 0.85) {
  if (!window.speechSynthesis || !dialogues?.length) return;
  try { await loadVoices(); } catch { /* 静默降级 */ }

  window.speechSynthesis.cancel();
  _lastVoice = null;

  let index = 0;
  const speakNext = () => {
    if (index >= dialogues.length) return;
    const line = dialogues[index];
    if (!line.text) { index++; speakNext(); return; }

    const utterance = new SpeechSynthesisUtterance(line.text);
    utterance.lang = "en-US";
    utterance.rate = rate;

    const voice = pickVoice(line.gender || "female");
    if (voice) utterance.voice = voice;

    utterance.onend = () => { index++; setTimeout(speakNext, 80); };
    utterance.onerror = () => { index++; setTimeout(speakNext, 80); };
    window.speechSynthesis.speak(utterance);
  };
  speakNext();
}

/** 停止朗读 */
function stopSpeaking() {
  if (window.speechSynthesis) window.speechSynthesis.cancel();
}

export function useSpeech() {
  return { speakText, speakDialogues, stopSpeaking };
}
