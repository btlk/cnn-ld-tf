$(document).ready(function() {
  /* initial rendering */

  var file_content = "";
  var recog_text = "";

  var chart = new CanvasJS.Chart("chartContainer",
    {
      title:{
        text: "Top 10 Predictions",
        fontFamily: "Helvetica",
        fontSize: 22
      },
      axisX: {
        labelFontFamily: "Helvetica",
        labelFontSize: 14
      },
      axisY: {
        title: "Score",
        titleFontFamily: "Helvetica",
        titleFontSize: 18,
        labelFontFamily: "Helvetica",
        labelFontSize: 14
      },
      data: [{
        type: "column",
        dataPoints: [
          {x: 10, y: 473.721, label: 'Japanese'},
          {x: 20, y: 99.5272, label: 'Greek'},
          {x: 30, y: 76.0632, label: 'Thai'},
          {x: 40, y: 60.9401, label: 'Urdu'},
          {x: 50, y: 52.9983, label: 'Sinhalese'},
          {x: 60, y: 21.5522, label: 'Georgian'},
          {x: 70, y: 20.3253, label: 'Hebrew'},
          {x: 80, y: 11.8332, label: 'Nepali'},
          {x: 90, y: 9.92754, label: 'Mongolian'},
          {x: 100, y: -1.77319, label: 'Telugu'}
        ]
      }]
    });
  chart.render();


  /* Redraw Prediction */
  $('#send-text').on('click', function() {
    var radios_detect_from = document.getElementsByName('detect_from');
    var text = "";
    if (radios_detect_from[0].checked) {
      text = $("#get-text").val();
    } else {
      text = file_content;
    }
    if (text == "") {
      alert("Document is empty!");
      return false;
    }
    recog_text = text;
    var host = 'http://localhost:5000';
    //sanitize
    text = text.replace(/[.,\/@#!?$%\^&\*;:{}\"=+\/\\-_`~()<>|'\[\]0-9]/g,"");
    text = text.replace(/\s{2,}/g," ");
    if (text == "" || text == " ") {
      alert("String for detection is empty!");
      return false;
    }
    host = host.replace(/(\/)$/, '');
    console.log(host + "/predict?text=" + text);

    var pred = '';
    var scores = {};
    $.ajax({
      type: "POST",
      url: host + "/predict?text=" + text,
      contentType: "application/json; charset=utf-8",
      async: false,
      processData: false,
      dataType: "json",
      success: function (data) {
        //console.log(data);
        pred = data.prediction;
        scores = data.scores;
      },
      error: function(XMLHttpRequest, textStatus, errorThrown){
        pred = '';
        scores = {};
        alert('Error : ' + errorThrown);
      }
    });
    //console.log(Object.keys(scores).length , scores);

    if (Object.keys(scores).length > 0){
      //alert(pred);
      var dataPoints = [];
      $.each( scores, function( key, value ) {
        //console.log( key + ": " + value );
        dataPoints.push({'y': value, 'label': key });
      });
      dataPoints.sort(
        function(a, b) {
          return b['y'] - a['y']
        }
      );
      $.each( dataPoints, function( i, value ) {
        if (i < 10){
          value['x'] = (i * 10) + 10;
        }
      });
      //console.log(dataPoints.slice(0, 10))
      //console.log(pred);
      //console.log(scores[pred]);
      $('#prediction').text(pred);
      $('#score').text(scores[pred]);


      var chart = new CanvasJS.Chart("chartContainer",
        {
          title:{
            text: "Top 10 Predictions",
            fontFamily: "Helvetica",
            fontSize: 22
          },
          axisX: {
            labelFontFamily: "Helvetica",
            labelFontSize: 14
          },
          axisY: {
            title: "Score",
            titleFontFamily: "Helvetica",
            titleFontSize: 18,
            labelFontFamily: "Helvetica"
          },
          data: [{
            type: "column",
            dataPoints: dataPoints.slice(0, 10)
          }]
        });
      chart.render();

    }

    return false; // abort reload
  });

  $('#set-text-from-file').change(function (event) {
      var fileToLoad = document.getElementById("set-text-from-file").files[0];
      var filename = this.value.replace(/^.*[\\\/]/, '');
      var fileReader = new FileReader();
      fileReader.onload = function(fileLoadedEvent) 
      {
          var textFromFileLoaded = fileLoadedEvent.target.result;
          file_content = textFromFileLoaded;
          document.getElementById("filepath").innerHTML = filename;
          //document.getElementById("get-text").value = textFromFileLoaded;
      };
      fileReader.readAsText(fileToLoad, "UTF-8"); 
  });

  function add_zero(s) {
    if (s.length < 2) {
      s = "0" + s;
    }
    return s;
  }

  $('#save-result').on('click', function() {
      var date = new Date();
      var dd = add_zero(String(date.getDate()));
      var mm = add_zero(String(date.getMonth() + 1));
      var yyyy = String(date.getFullYear());
      var hh = add_zero(String(date.getHours()));
      var min = add_zero(String(date.getMinutes()));
      var ss = add_zero(String(date.getSeconds()));

      var chp_date = dd + "." + mm + "." + yyyy + "_" + hh + "." + min + "." + ss;
      var chp_prediction = document.getElementById("prediction").innerHTML;
      var chp_score = document.getElementById("score").innerHTML;
      var chp_text = recog_text;

      var chp_total = chp_date + '\n' + chp_prediction +'\n' + chp_score + '\n' + chp_text;

      var element = document.createElement('a');
      element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(chp_total));
      element.setAttribute('download', chp_date + "_" + chp_prediction + ".txt");
      element.style.display = 'none';
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
  });

  $('#load-result').change(function (event) {
      var fileToLoad = document.getElementById("load-result").files[0];
      var fileReader = new FileReader();
      fileReader.onload = function(fileLoadedEvent) 
      {
          var textFromFileLoaded = fileLoadedEvent.target.result;
          var lines = textFromFileLoaded.split('\n');
          if (lines.length < 4) {
            alert("Checkpoint is corrupted! Unable to load.");
            return;
          }
          if (isNaN(parseFloat(lines[2]))) {
            alert("Checkpoint's score is not a number! Unable to load.");
            return;
          }
          document.getElementById("prediction").innerHTML = lines[1];
          document.getElementById("score").innerHTML = lines[2];
          var s_text = "";
          for (var line = 3; line < lines.length; ++line) {
            s_text += lines[line] + "\n";
          }
          document.getElementById("get-text").value = s_text;
          document.getElementById("chartContainer").innerHTML = "";
          //document.getElementById("get-text").value = textFromFileLoaded;
      };
      fileReader.readAsText(fileToLoad, "UTF-8"); 
  });
});
