// #define USE_VLD //Uncomment for Visual Leak Detector.
#if (defined _MSC_VER && defined USE_VLD)
#include <vld.h>
#endif

// Include automatically generated configuration file if running autoconf
#include "config.h"

#ifdef USING_GETTEXT
#include <libintl.h>
#include <locale.h>
#define _(x) gettext(x)
#else
#define _(x) (x)
#endif
#include "allheaders.h"
#include "baseapi.h"
#include "ctype.h"
#include "strngs.h"
#ifdef __darwin__
	#include "fmemopen.h"
#endif

bool isLibLept() {

	#if defined(HAVE_LIBLEPT)
		return true;
	#else
		return false;
	#endif
	}

bool isLibTiff() {
	#if defined(HAVE_LIBLEPT)
		return true;
	#else
		return false;
	#endif
	}
//  useless <<<<<<<<
int readBuf(const char *fname,l_uint8 *buf) {
	FILE *fp;
	long len;
	fp=fopen(fname,"rb");
	fseek(fp,0,SEEK_END); //go to end
	len=ftell(fp); //get position at end (length)
	fseek(fp,0,SEEK_SET); //go to beg.
	buf=(l_uint8 *)malloc(len); //malloc buffer
	fread(buf,len,1,fp); //read into buffer
	fclose(fp);
	return len;
}


char* ProcessPagesWrapper(const char* image,tesseract::TessBaseAPI* api) {
	//printf("ok->%s",text_out);
	STRING mstr; 
	api->ProcessPages(image, NULL, 0, &mstr);
	const char *tmpStr=mstr.string();
	char *retStr = new char[strlen(tmpStr) + 1];
	strcpy (retStr,tmpStr);
	return retStr;
 }                


char* ProcessPagesPix(const char* image,tesseract::TessBaseAPI* api) {
	STRING mstr; 
	int page=0;
	Pix *pix;
	pix = pixRead(image);
	//l_uint8 buf[10000];
	//int len=readBuf(image,buf);
	//if (len < 0) 
	//	puts("Cannot Read Buffer");
	api->ProcessPage(pix, page, NULL, NULL, 0, &mstr);
	const char *tmpStr=mstr.string();
	char *retStr = new char[strlen(tmpStr) + 1];
	strcpy (retStr,tmpStr);
	//printf("ok->%s",retStr);
	return retStr;
 }
 
     
char* ProcessPagesFileStream(const char* image,tesseract::TessBaseAPI* api) {
	
	Pix *pix;
	STRING mstr;
	int page=0;
	FILE *fp=fopen(image,"rb");
	pix=pixReadStream(fp,0);
	api->ProcessPage(pix, page, NULL, NULL, 0, &mstr);
	const char *tmpStr=mstr.string();
	char *retStr = new char[strlen(tmpStr) + 1];
	strcpy (retStr,tmpStr);
	//printf("ok->%s",retStr);
	fclose(fp);
	return retStr;
 }
void dump_buffer(void *buffer, int buffer_size)
{
  int i;
  for(i = 0;i < buffer_size;++i)
     printf("%c", ((char *)buffer)[i]);
}

char* ProcessPagesBuffer(char* buffer, int fileLen, tesseract::TessBaseAPI* api) {
	
	FILE *stream;
	//int ch;
	stream=fmemopen((void*)buffer,fileLen,"rb");
	//int count;
	//while ((ch = fgetc (stream)) != EOF)
	//	printf ("Got %d:%c\n", count++,ch);
	//fclose (stream);
	//puts("''''''''''''''''''");
	
	Pix *pix;
	int page=0;
	STRING mstr;
	
	pix=pixReadStream(stream,0);
	api->ProcessPage(pix, page, NULL, NULL, 0, &mstr);
	const char *tmpStr=mstr.string();
	char *retStr = new char[strlen(tmpStr) + 1];
	strcpy (retStr,tmpStr);
	//printf("ok->%s",retStr);

	return retStr;
 }
 
char* ProcessPagesRaw(const char* image,tesseract::TessBaseAPI* api) {
	

	FILE *fp=fopen(image,"rb");
	//Get file length
	fseek(fp, 0, SEEK_END);
	int fileLen=ftell(fp);
	fseek(fp, 0, SEEK_SET);
	printf("fileLen=%d\n",fileLen);
	char *buffer;
	//Allocate memory
	buffer=(char *)malloc(fileLen+1);
	if (!buffer)
	{
		fprintf(stderr, "Memory error!");
        fclose(fp);
		return NULL ;
	}
	int n;
	n = fread(buffer,fileLen, 1, fp);
	fclose(fp);
	printf("n=%d\n",n);
	//dump_buffer(buffer,fileLen);
	char* retStr;
	retStr=ProcessPagesBuffer(buffer,fileLen, api);
	//Free memory
	free(buffer);
	return retStr;
 }

/*
	Special functions for DiscoveryGarden and OurDigitalWorld
*/
int ExtractResultsWrapper(tesseract::TessBaseAPI* api, char *outfile, int chars_limit, char *valid_chars) {
    char *words;
    int *lengths;
    float *costs;
    int *x0;
    int *y0;
    int *x1;
    int *y1;
    char *char_4_coords;
    int *char_x0;
    int *char_y0;
    int *char_x1;
    int *char_y1;

    //allocate space here, we know the number of chars at this point
    char_4_coords = new char[chars_limit];
    char_x0 = new int[chars_limit];
    char_y0 = new int[chars_limit];
    char_x1 = new int[chars_limit];
    char_y1 = new int[chars_limit];

    //the all important call
    api->TesseractExtractResult(&words, &lengths, &costs,
        &x0, &y0, &x1, &y1,&char_4_coords,&char_x0,&char_y0,
	&char_x1,&char_y1,api->page_res_, chars_limit);

    FILE *coordfile = NULL;
    coordfile = fopen(outfile, "w");

    int wordsLen = strlen(char_4_coords);
    int tmp_cnt = 0;

    for (int i = 0; i < wordsLen; i++) {
       if (strlen(valid_chars) == 0 || strchr(valid_chars,char_4_coords[i])) {
          fprintf(coordfile,"%c %d %d %d %d\n",char_4_coords[i],char_x0[i],
             char_y0[i],char_x1[i],char_y1[i]);
          tmp_cnt++;
       }//if
    }//for
            
    fclose(coordfile);

    return tmp_cnt;
}

char* ExtractResultsArrayWrapper(tesseract::TessBaseAPI* api, int chars_limit, char *delimit, char *valid_chars) {
    char *buffer;
    char *retStr;
    char *words;
    int *lengths;
    float *costs;
    int *x0;
    int *y0;
    int *x1;
    int *y1;
    char *char_4_coords;
    int *char_x0;
    int *char_y0;
    int *char_x1;
    int *char_y1;
        

    //allocate space here, we know the number of chars at this point
    char_4_coords = new char[chars_limit];
    char_x0 = new int[chars_limit];
    char_y0 = new int[chars_limit];
    char_x1 = new int[chars_limit];
    char_y1 = new int[chars_limit];

    //the all important call
    api->TesseractExtractResult(&words, &lengths, &costs,
        &x0, &y0, &x1, &y1,&char_4_coords,&char_x0,&char_y0,
	&char_x1,&char_y1,api->page_res_, chars_limit);

    int wordsLen = strlen(char_4_coords);
    int tmp_cnt = 0;

    buffer=(char *)malloc(100);
    retStr=(char *)malloc(100 * wordsLen);
    strcpy(retStr,"");

    for (int i = 0; i < wordsLen; i++) {
       if (strlen(valid_chars) == 0 || strchr(valid_chars,char_4_coords[i]) <= 0) {
          if (tmp_cnt > 0) {
             strcat(retStr,delimit);
          }
          sprintf(buffer,"%c %d %d %d %d",char_4_coords[i],char_x0[i],
             char_y0[i],char_x1[i],char_y1[i]);
          strcat(retStr,buffer);
          tmp_cnt++;
       }//if
    }//for
            
    return retStr;
}
