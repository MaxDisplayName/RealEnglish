/**
 * 台词解析工具。
 * 将 [角色名]文本 格式的对话解析为结构化的 {speaker, text, gender} 数组。
 * 支持多行和单行混合格式。
 */

/** 常见男性角色名/代词（不区分大小写） */
const MALE_SPEAKERS = new Set([
  "man", "he", "him", "richard", "harry", "ron", "hermione",
  "phil", "jay", "mitch", "cam", "luke", "manny", "joe",
  "alex", "liam", "noah", "oliver", "elijah", "james",
  "henry", "lucas", "jack", "leo", "michael", "daniel",
  "david", "robert", "john", "paul", "george", "tom",
  "narrator", "mr.", "mr", "sir", "father", "dad", "son",
  "brother", "uncle", "grandpa", "king",
]);

/** 常见女性角色名/代词 */
const FEMALE_SPEAKERS = new Set([
  "woman", "she", "her", "martha", "lily", "ginny", "molly",
  "claire", "haley", "gloria", "lily", "phoebe", "monica",
  "rachel", "emma", "olivia", "ava", "isabella", "sophia",
  "mia", "charlotte", "amelia", "harper", "evelyn", "abigail",
  "mrs.", "mrs", "ms.", "ms", "miss", "mother", "mom",
  "sister", "aunt", "grandma", "queen", "princess",
]);

/** 中性角色（用女声朗读） */
const NEUTRAL_FEMALE = new Set([
  "narrator", "announcer", "voice", "teacher",
]);

/**
 * 判断角色性别。
 * @param {string} speaker - 角色名
 * @returns {'male' | 'female'}
 */
function detectGender(speaker) {
  const key = speaker.replace(/[^a-zA-Z]/g, "").toLowerCase().trim();
  if (MALE_SPEAKERS.has(key)) return "male";
  // 默认返回 female（女声通常更清晰，适合语言学习）
  return "female";
}

/**
 * 解析原始台词文本。
 * @param {string} rawText - 原始台词，格式为 [角色]文本\n[角色]文本
 * @param {Object|null} genderMap - 可选的服务器端性别映射，如 {"Woman":"female","Man":"male"}
 * @returns {Array<{speaker: string, text: string, gender: string, raw: string}>}
 */
export function parseDialogue(rawText, genderMap = null) {
  if (!rawText) return [];

  const lines = [];
  // 匹配 [角色名]文本 格式
  const pattern = /\[([^\]]+)\]\s*([^[]*)/g;
  // 也匹配 "角色名：文本" 格式
  const pattern2 = /^([A-Za-z\s.]+)[：:]\s*(.+)$/gm;

  let match;
  let hasBracketMatches = false;

  while ((match = pattern.exec(rawText)) !== null) {
    hasBracketMatches = true;
    const speaker = match[1].trim();
    const text = match[2].trim();
    if (text) {
      // 优先使用服务器端提供的性别映射
      const gender = genderMap?.[speaker] || detectGender(speaker);
      lines.push({
        speaker,
        text,
        gender,
        raw: match[0],
      });
    }
  }

  // 如果没匹配到 [角色] 格式，尝试 "角色：文本" 格式
  if (!hasBracketMatches) {
    while ((match = pattern2.exec(rawText)) !== null) {
      const speaker = match[1].trim();
      const text = match[2].trim();
      if (text) {
        const gender = genderMap?.[speaker] || detectGender(speaker);
        lines.push({
          speaker,
          text,
          gender,
          raw: match[0],
        });
      }
    }
  }

  // 如果都没匹配到，当作单条无角色文本
  if (lines.length === 0 && rawText.trim()) {
    lines.push({
      speaker: "",
      text: rawText.trim(),
      gender: "female",
      raw: rawText.trim(),
    });
  }

  return lines;
}

/**
 * 从台词文本中提取纯文本（去掉角色标记）。
 * @param {string} rawText
 * @returns {string}
 */
export function extractPlainText(rawText) {
  return rawText.replace(/\[[^\]]*\]\s*/g, "").trim();
}
