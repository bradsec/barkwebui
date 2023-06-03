document.addEventListener('DOMContentLoaded', function() {
  const socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

  const generateButton = document.getElementById('generate-button');
  const audioList = document.getElementById('audio-list');
  // const progressBar = document.getElementById('progress-bar');
  const progressContainer = document.querySelector('.progress-container');
  const progressComplete = document.querySelector('.progress-complete');

  document.getElementById('generator-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const textInput = document.getElementById('text-input').value;
    const voice = document.getElementById('voice').value;
    const textTemp = document.getElementById('text-temp').value;
    const waveformTemp = document.getElementById('waveform-temp').value;
    const reduceNoise = document.getElementById('reduce-noise').checked;
    const removeSilence = document.getElementById('remove-silence').checked;
    const speed = document.getElementById('speed').value;
    const pitch = document.getElementById('pitch').value;

    // Check if text is empty focus
    if (textInput.trim() === '') {
      document.getElementById('text-input').focus()
      return;
    }

    localStorage.setItem('textInput', textInput);
    localStorage.setItem('voice', voice);
    localStorage.setItem('textTemp', textTemp);
    localStorage.setItem('waveformTemp', waveformTemp);
    localStorage.setItem('reduceNoise', reduceNoise);
    localStorage.setItem('removeSilence', removeSilence);
    localStorage.setItem('speed', speed);
    localStorage.setItem('pitch', pitch);

    socket.emit('start_generation', {text_input: textInput, voice: voice, text_temp: textTemp, waveform_temp: waveformTemp, reduce_noise: reduceNoise, remove_silence: removeSilence, speed: speed, pitch: pitch});
    generateButton.disabled = true;
    progressComplete.textContent = "";
    
    // Reset the progress bar
    progress.style.strokeDashoffset = circumference;
    progress.style.animation = 'spin 4s linear infinite';
    progressText.textContent = '0%';
      

    // Show the progress bar
    progressContainer.classList.remove('hide');
    progressComplete.classList.remove('hide');
  });

  let progress = document.querySelector('#progress');
  let progressText = document.querySelector('#progress-text');
  let radius = progress.r.baseVal.value;
  let circumference = 2 * Math.PI * radius;
  
  progress.style.strokeDasharray = `${circumference} ${circumference}`;
  progress.style.strokeDashoffset = `${circumference}`;
  
  function setProgress(percent) {
    progress.style.animation = 'none'; // Remove the animation
    const offset = circumference - percent / 100 * circumference;
    progress.style.strokeDashoffset = offset;
    progressText.textContent = `${Math.round(percent)}%`;
  }
  
  
  // Update the progress bar
  socket.on('generation_progress', function(data) {
    console.log('Generation progress:', data.progress);
    setProgress(data.progress * 100);
  });  

  socket.on('generation_complete', function(data) {
    console.log('Generation completed:', data);
  
    generateButton.disabled = false;
    progressContainer.classList.add('hide');
    progressComplete.textContent = "Generation completed in " + formatTime(data.generation_time) + ".";
  
    // Scroll to the top of audio-list
    progressComplete.scrollIntoView({ behavior: 'smooth' });

    // Highlight new card
    isNewCard = true;
  
    // Load the updated audio list if the progress bar is not visible
    if (progressContainer.classList.contains('hide')) {
      loadAudioList(() => {
        isNewCard = false;
      });
    }
  });

let sampleText = "This is my voice. There are many like it, but this one is mine. It is my vocal instrument. I must master it as I must master my performance. Without me, my voice is silent. Without my voice, I am unheard. I must speak with clarity. I must captivate the audience better than anyone else."

// Check local storage
document.getElementById('text-input').value = localStorage.getItem('textInput') || sampleText;
document.getElementById('voice').value = localStorage.getItem('voice') || 'announcer';
document.getElementById('text-temp').value = localStorage.getItem('textTemp') || '0.7';
document.getElementById('waveform-temp').value = localStorage.getItem('waveformTemp') || '0.7';
document.getElementById('speed').value = localStorage.getItem('speed') || '1.0';
document.getElementById('pitch').value = localStorage.getItem('pitch') || '0';
document.getElementById('reduce-noise').checked = localStorage.getItem('reduceNoise') === 'true';
document.getElementById('remove-silence').checked = localStorage.getItem('removeSilence') === 'true';    

// Load the audio list on page load
loadAudioList();

const audioItemTemplate = document.getElementById('audio-item-template').content;
let isNewCard = false;

function loadAudioList(callback) {
  // Clear the existing audio list
  audioList.innerHTML = '';

  // Fetch the JSON data
  fetch('static/json/barkwebui.json')
    .then(response => {
      if (!response.ok) {
        throw new Error('JSON data file not found');
      }
      return response.json();
    })
    .then(data => {
      for (const key in data) {
        if (data.hasOwnProperty(key)) {
          const item = data[key];
          const filename = item.outputFile;
          const textInput = item.textInput;
          const genTime = item.generationTime;
          const voice = item.voice;
          const textTemp = item.textTemp;
          const waveformTemp = item.waveformTemp;
          const speed = item.speed;
          const pitch = item.pitch;
          const reduceNoise = item.reduceNoise;
          const removeSilence = item.removeSilence;

          // Create a new audio item using the template
          const audioItem = audioItemTemplate.cloneNode(true);
          audioItem.querySelector('.audio-player').src = 'static/output/' + filename;
          audioItem.querySelector('.filename').textContent = filename;
          audioItem.querySelector('.gen-time').textContent = 'Generation Time: ' + formatTime(genTime);
          audioItem.querySelector('.voice').textContent = 'Voice: ' + voice;
          audioItem.querySelector('.text-temp').textContent = 'Text Temp: ' + textTemp;
          audioItem.querySelector('.waveform-temp').textContent = 'Waveform Temp: ' + waveformTemp;
          audioItem.querySelector('.speed').textContent = 'Speed: ' + speed;
          audioItem.querySelector('.pitch').textContent = 'Pitch: ' + pitch;
          audioItem.querySelector('.reduce-noise').textContent = 'RN: ' + reduceNoise;
          audioItem.querySelector('.remove-silence').textContent = 'RS: ' + removeSilence;
          audioItem.querySelector('.text-input').textContent = textInput;

          audioItem.querySelector('.download-button').addEventListener('click', function(event) {
            event.preventDefault();
            downloadFile('static/output/' + filename, filename);
          });

          audioItem.querySelector('.delete-button').addEventListener('click', function(event) {
            event.preventDefault();
            const parentCard = event.target.closest('.card');
          
            // Check if the parentCard has the 'new-card' class
            if (parentCard.classList.contains('new-card')) {
              progressComplete.textContent = "";
            }
          
            parentCard.classList.add('hide');
            deleteAudioFile(filename);
          });

          if (isNewCard) {
            audioItem.querySelector('.card').classList.add('new-card');
            isNewCard = false;
          }

          audioList.appendChild(audioItem);
        }
      }
    })
    .catch(error => {
      if (error.message === 'JSON data file not found') {
        console.log('barkwebui.json file does not exist');
      } else {
        console.log('Error loading audio list:', error);
      }
    })
    .finally(() => {
      if (callback) callback();
    });
}


  function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.target = '_blank';
    link.click();
  }

  function deleteAudioFile(filename) {
    fetch('static/output/' + filename, { method: 'DELETE' })
      .then(function() {
        // Refresh the audio list
        console.log('File deleted: ', filename);
      })
      .catch(function(error) {
        console.log('Error deleting file: ', error);
      });
  }

  const moreInfoLinks = document.querySelectorAll('.more-info-link');

  moreInfoLinks.forEach(link => {
    link.addEventListener('click', function() {
      const moreInfo = this.previousElementSibling;
      moreInfo.classList.toggle('show');
      this.textContent = moreInfo.classList.contains('show') ? 'Less Info' : this.dataset.defaultText;
    });
  
    link.dataset.defaultText = link.textContent; 
  });

  var selectContainers = document.querySelectorAll('.select-container');

  selectContainers.forEach(function(container) {
    var select = container.querySelector('select');
    
    select.addEventListener('focus', function() {
      container.classList.add('open');
    });
    
    select.addEventListener('blur', function() {
      container.classList.remove('open');
    });
  });

  function formatTime(seconds) {
    let hours = Math.floor(seconds / 3600);
    let minutes = Math.floor((seconds % 3600) / 60);
    seconds = Math.floor(seconds % 60);

    let timeStr = '';
    
    if (hours > 0) {
      timeStr += `${hours} hours, `;
    }
    
    if (minutes > 0) {
      timeStr += `${minutes} minutes, `;
    }
  
    timeStr += `${seconds} seconds`;
    return timeStr;
  }  
});
