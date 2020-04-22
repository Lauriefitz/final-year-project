var AWS = require('aws-sdk');
var s3 = new AWS.S3();

exports.handler = (event, context, callback) => {  
    var kbucketName = 'caller-details';
    var kkeyName = 'status.txt';
    var known;
    var last_caller = 'last_caller.txt'
    var lastCaller;
    readFile(kbucketName, last_caller, onError, function(response){
                lastCaller = response;
                switch (event.request.type) {
                    case "LaunchRequest":
                        console.log("here");
                        context.succeed(generateResponse(buildSpeechletResponse("Welcome to Alexa, Who's at the Door.", false)));
                        break;
                        case "IntentRequest":
                            switch (event.request.intent.name) {
                                case "Time":
                                    context.succeed(generateResponse(buildSpeechletResponse(lastCaller, false)));
                                    break;
                            }
                            break;
                }
                
            })
    readFile(kbucketName, kkeyName, onError, function(response){
        known = response;
        console.log(known);
        if (known == "true"){
            var bucketName = 'caller-details';
            var keyName = 'caller_name.txt';
            var name;
            readFile(bucketName, keyName, onError, function(response){
                name = response;
                switch (event.request.type) {
                    case "LaunchRequest":
                        console.log("here");
                        context.succeed(generateResponse(buildSpeechletResponse("Welcome to Alexa, Who's at the Door.", false)));
                        break;
                        case "IntentRequest":
                            switch (event.request.intent.name) {
                                case "DoorQuery":
                                    context.succeed(generateResponse(buildSpeechletResponse(name + " is at the door!", false)));
                                    console.log("It looks like " + name);
                                    break;
                            }
                            break;
                    
                }
                
            });
            
        }
        if (known == "false"){
            console.log("Unknown: " + known);
            var ubucketName = 'caller-details';
            var ukeyName = 'caller_unknown.txt';
            var details;
            readFile(ubucketName, ukeyName, onError, function(response){
                details = response;
                switch (event.request.type) {
                    case "LaunchRequest":
                        console.log("here");
                        context.succeed(generateResponse(buildSpeechletResponse("Welcome to Alexa, Who's at the Door.", false)));
                        break;
                        case "IntentRequest":
                            switch (event.request.intent.name) {
                                case "DoorQuery":
                                    context.succeed(generateResponse(buildSpeechletResponse(details, false)));
                                    
                                    break;
                                
                            }
                            break;
                    
                }
                
            });
        }
        else{
            console.log("Error");
            
        }
    });
};
        
function readFile (bucketName, filename, onError, callback) {
    var params = { Bucket: bucketName, Key: filename };
    var name;
    s3.getObject(params, function (err, data) {
        if (!err){
            name = (data.Body.toString());
            //console.log("It's " + name);
            //return name;
        }
        else{
            console.log(err);
        }
        return callback(name);
    });
}
        
function onError (err) {
    console.log('error: ' + err);
}      

function buildSpeechletResponse(outputText, shouldEndSession) {
    return {
        outputSpeech: {
            type: "PlainText",
            text: outputText
        },
        shouldEndSession: shouldEndSession
        
    }
}

function generateResponse(speechletResponse) {
    return {
        version: "1.0",
        response: speechletResponse
        
    }
}