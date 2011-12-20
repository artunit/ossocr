bool isLibTiff(); 
bool isLibLept(); 
char* ProcessPagesWrapper(const char* image,tesseract::TessBaseAPI* api);
int ExtractResultsWrapper(tesseract::TessBaseAPI* api, char *outfile);
char* ProcessPagesPix(const char* image,tesseract::TessBaseAPI* api);
char* ProcessPagesFileStream(const char* image,tesseract::TessBaseAPI* api);
char* ProcessPagesBuffer(char* buffer, int fileLen, tesseract::TessBaseAPI* api);
char* ProcessPagesRaw(const char* image,tesseract::TessBaseAPI* api);
