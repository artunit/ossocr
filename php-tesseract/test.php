<?php 
include("tesseract.php");
if (!extension_loaded('tesseract')) {
    print("not loaded\n");
} else {
    print("loaded\n");
}
$mImgFile = "eurotext.tif";
print("hello world\n");
$api = new TessBaseAPI();
    
$api->SetPageSegMode(tesseract::PSM_AUTO);
$tessdatapath = getenv('TESSDATA_PREFIX');
$api->Init($tessdatapath,"eng",tesseract::OEM_DEFAULT);

print("now try to do ocr\n");
$result=tesseract::ProcessPagesWrapper($mImgFile,$api);
printf("%s\n",$result);

$lenresult = tesseract::ExtractResultsWrapper($api, "coords.txt", strlen($result),"");
printf("%d\n", $lenresult);

?>
