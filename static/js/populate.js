// Helper function to populate a dropdown with options
function populateDropdown(
  dropdown,
  values,
  labelPrefix = "",
  specialZeroLabel = null
) {
  values.forEach((value) => {
    let prefix = labelPrefix;
    if (labelPrefix.includes("Speed")) {
      labelPrefix = "Speed ";
      label = `${labelPrefix}${value}x`;
    } else if (labelPrefix.includes("Pitch") && value > 0) {
      prefix = `${labelPrefix}+`;
      label = `${prefix}${value}`;
    } else {
      label = `${prefix}${value}`;
    }
    if (value === 0 && specialZeroLabel) {
      label = specialZeroLabel;
    }
    const option = new Option(label, value);
    dropdown.add(option);
  });
}

const voiceDropdown = document.getElementById("voice");
const speedDropdown = document.getElementById("speed");
const pitchDropdown = document.getElementById("pitch");
const waveformTempDropdown = document.getElementById("waveform-temp");
const textTempDropdown = document.getElementById("text-temp");

const voiceModels = [
  "v2/en",
  "v2/de",
  "v2/es",
  "v2/fr",
  "v2/hi",
  "v2/it",
  "v2/ja",
  "v2/ko",
  "v2/pl",
  "v2/pt",
  "v2/ru",
  "v2/tr",
  "v2/zh",
  "en",
  "de",
  "es",
  "fr",
  "hi",
  "it",
  "ja",
  "ko",
  "pl",
  "pt",
  "ru",
  "tr",
  "zh",
];
const numVoices = 10;

const speedValues = [0.1, 0.25, 0.5, 0.75, 0.9, 1.1, 1.25, 1.5, 1.75, 1.9, 2.0];
const pitchValues = [
  -12, -11, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
  11, 12,
];
const waveformTempValues = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];
const textTempValues = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];

for (let pattern of voiceModels) {
  for (let i = 0; i < numVoices; i++) {
    const voiceValue = `${pattern}_speaker_${i}`;
    const voiceText = getVoiceText(pattern, i);
    if (!voiceOptionExists(voiceDropdown, voiceValue)) {
      const option = new Option(voiceText, voiceValue);
      voiceDropdown.add(option);
    }
  }
}

function getVoiceText(pattern, index) {
  return pattern === "v2/en"
    ? `en v2 speaker ${index}`
    : `${pattern} speaker ${index}`;
}

function voiceOptionExists(dropdown, value) {
  return Array.from(dropdown.options).some((option) => option.value === value);
}

populateDropdown(speedDropdown, speedValues, "Speed ", "Normal Speed");
populateDropdown(pitchDropdown, pitchValues, "Pitch ", "Normal Pitch");
populateDropdown(waveformTempDropdown, waveformTempValues, "Waveform Temp ");
populateDropdown(textTempDropdown, textTempValues, "Text Temp ");
