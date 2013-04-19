bool isLibTiff(); 
bool isLibLept(); 
char* ProcessPagesWrapper(const char* image,tesseract::TessBaseAPI* api);
char* ProcessPagesPix(const char* image,tesseract::TessBaseAPI* api);
char* ProcessPagesFileStream(const char* image,tesseract::TessBaseAPI* api);
char* ProcessPagesBuffer(char* buffer, int fileLen, tesseract::TessBaseAPI* api);
char* ProcessPagesRaw(const char* image,tesseract::TessBaseAPI* api);
int ExtractResultsWrapper(tesseract::TessBaseAPI* api, char *outfile, int chars_length, char* chars_limit);
char* ExtractResultsArrayWrapper(tesseract::TessBaseAPI* api, int chars_limit, char *delimit, char *valid_chars);
