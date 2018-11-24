 // get url data, store locally and set server 8080
var fs = require('fs');

var http = require('http');
var server;
var request = require('request');
request('http://time.jsontest.com', function (error, response, body) {
  if (!error && response.statusCode == 200) {
     var importedJSON = JSON.parse(body);
	 var jstring = JSON.stringify(importedJSON);
	 
	 fs.writeFile("./test1.json", jstring, function(err) {
    if(err) {
        return console.log(err);
    }

    console.log("The file was saved!");
});
	 
	 
     console.log(importedJSON);
	 
  }
})

var sdata=require('./test1.json');
server = http.createServer(function(req,res){
	// Set CORS headers
	res.setHeader('Access-Control-Allow-Origin', '*');
	res.setHeader('Access-Control-Request-Method', '*');
	res.setHeader('Access-Control-Allow-Methods', 'OPTIONS, GET');
	res.setHeader('Access-Control-Allow-Headers', "*");
	res.end(JSON.stringify(sdata));
	//if ( req.method === 'OPTIONS' ) {
		////res.writeHead(200);
		//res.end();
		//return;
	//}

}).listen(8080);


