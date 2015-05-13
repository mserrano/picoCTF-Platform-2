#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>

#include <errno.h>

void explode_bomb() {
  printf("Sorry, incorrect!\n");
  printf("BOOOOM\n");
  exit(0);
}

int string_length(char *s) {
  int result = 0;
  for (result = 0; s[result]; result++);
  return result;
}

int strings_not_equal(char *a, char *b) {
  int v2 = string_length(a);
  if (v2 != string_length(b))
    return 1;
  int i;
  for (i = 0; a[i]; i++) {
    if (a[i] != b[i])
      return 1;
  }
  return 0;
}

void phase_1(char *input) {
  int result = strings_not_equal(input, "Public speaking is very easy.");
  if (result) {
    explode_bomb();
  }
}

void read_six_numbers(char *input, int *array) {
  int result;
  result = sscanf(input, "%d %d %d %d %d %d",
    &array[0], &array[1], &array[2], &array[3], &array[4], &array[5]);
  if (result <= 5) {
    explode_bomb();
  }
}

void phase_2(char *input) {
  int array[6];
  read_six_numbers(input, array);
  if (array[0] != 1)
    explode_bomb();
  int f = 1;
  int i;
  for (i = 1; i < 6; i++) {
    f = array[i - 1] * (i + 1);
    if (array[i] != f)
      explode_bomb();
  }
}

void phase_3(char *input) {
  int v3;
  char v4;
  int v5;
  char v2;
  if (sscanf(input, "%d %c %d", &v3, &v4, &v5) <= 2)
    explode_bomb();
  switch(v3) {
  case 0:
    v2 = 113;
    if (v5 != 777)
      explode_bomb();
    break;
  case 1:
    v2 = 98;
    if (v5 != 214)
      explode_bomb();
    break;
  case 2:
    v2 = 98;
    if (v5 != 755)
      explode_bomb();
    break;
  case 3:
    v2 = 107;
    if (v5 != 251)
      explode_bomb();
    break;
  case 4:
    v2 = 111;
    if (v5 != 160)
      explode_bomb();
    break;
  case 5:
    v2 = 116;
    if (v5 != 458)
      explode_bomb();
    break;
  case 6:
    v2 = 118;
    if (v5 != 780)
      explode_bomb();
    break;
  case 7:
    v2 = 98;
    if (v5 != 524)
      explode_bomb();
    break;
  default:
    explode_bomb();
    break;
  }
  if (v2 != v4)
    explode_bomb();
}

int func(int inp) {
  int res;
  if (inp <= 1) {
    res = 1;
  } else {
    int v1 = func(inp - 1);
    res = v1 + func(inp - 2);
  }
  return res;
}

void phase_4(char *input) {
  int inp;
  if (sscanf(input, "%d", &inp) != 1)
    explode_bomb();
  if (inp <= 0)
    explode_bomb();
  int res = func(inp);
  if (res != 55)
    explode_bomb();
}

char arr_123[16] = {
  'i', 's', 'r', 'v', 'e', 'a', 'w', 'h', 'o', 'b', 'p',
  'n', 'u', 't', 'f', 'g'
};

void phase_5(char *input) {
  if (string_length(input) != 6)
    explode_bomb();
  char data[7];
  int i;
  for (i = 0; i < 6; i++) {
    data[i] = arr_123[(input[i] & 0xf)];
  }
  data[6] = 0;
  if (strings_not_equal(data, "giants"))
    explode_bomb();
}

struct node {
  int element;
  int unused;
  struct node *next;
};
typedef struct node node;

node node6 = { 0x1b0, 6, NULL };
node node5 = { 0x0d4, 5, &node6 };
node node4 = { 0x3e5, 4, &node5 };
node node3 = { 0x12d, 3, &node4 };
node node2 = { 0x2d5, 2, &node3 };
node node1 = { 0x0fd, 1, &node2 };

void phase_6(char *input) {
  int numbers[6];
  read_six_numbers(input, numbers);
  int v2 = 0;
  for (v2 = 0; v2 < 6; v2++) {
    if ((unsigned int)(numbers[v2] - 1u) > 5u)
      explode_bomb();
    int i;
    for (i = v2 + 1; i < 6; i++) {
      if (numbers[i] == numbers[v2])
        explode_bomb();
    }
  }

  node *nodes[6];
  int v4 = 0;
  for (v4 = 0; v4 < 6; v4++) {
    node *tmp = &node1;
    int j;
    for (j = 1; j < numbers[v4]; j++) {
      tmp = tmp->next;
    }
    nodes[v4] = tmp;
  }

  node *v7;
  node *v13;
  v7 = v13 = nodes[0];

  int v8;
  node *v9;
  for (v8 = 1; v8 < 6; v8++) {
    v9 = nodes[v8];
    v7->next = v9;
    v7 = v9;
  }
  v9->next = NULL;
  node *v10 = v13;
  int v11 = 0;
  for (v11 = 0; v11 < 5; v11++) {
    if (v10->element < v10->next->element)
      explode_bomb();
    v10 = v10->next;
  }
}

char input_string[1024];

char *read_line() {
  fgets(input_string, 80, stdin);
  input_string[strlen(input_string)-1] = '\0';
  return &input_string[0];
}

char username[1024];
void read_username() {
  fgets(username, 300, stdin);
}

int writen(int fd, char *buf, int count) {
  int so_far = 0;
  while (so_far < count) {
    int r = write(fd, buf, count);
    if (r < 0) {
      return r;
    }
    so_far += r;
  }
}

int writes(int fd, char *buf) {
  return writen(fd, buf, strlen(buf));
}

int phases_defused = 0;
void phase_defused() {
  phases_defused++;
  if (phases_defused == 6) {
    printf("Congratulations! You've defused the bomb! Submit your input!\n");
  }

  printf("Automatically submitting flag...\n");
  int clientfd;
  struct hostent *hp;
  struct sockaddr_in serveraddr;

  if ((clientfd = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
    printf("Could not submit the flag! Please submit it manually.\n");
    return;
  }

  if ((hp = gethostbyname("picodemo.derig.org")) == NULL) {
    printf("Could not submit the flag! Please submit it manually.\n");
    return;
  }

  bzero((char*)&serveraddr, sizeof(serveraddr));
  serveraddr.sin_family = AF_INET;
  bcopy((char*)hp->h_addr_list[0],
        &serveraddr.sin_addr.s_addr, hp->h_length);
  serveraddr.sin_port = htons(8891);

  if (connect(clientfd,
              (const struct sockaddr *)&serveraddr,
              sizeof(serveraddr)) < 0) {
    printf("Could not submit the flag! Please submit it manually.\n");
    return;
  }

  if (writes(clientfd, username) < 0) {
    printf("Could not submit the flag! Please submit it manually.\n");
    return;
  }
  if (writes(clientfd, "1697c2e9c0a690a86737779923417cb5\n") < 0) {
    printf("Could not submit the flag! Please submit it manually.\n");
    return;
  }
  int l = strlen(input_string);
  input_string[l] = '\n';
  input_string[l+1] = '\0';
  if (writes(clientfd, input_string) < 0) {
    printf("Could not submit the flag! Please submit it manually.\n");
    return;
  }
  int res;
  read(clientfd, &res, sizeof(int));
  close(clientfd);
  if (res != 0)
    printf("Flag accepted!\n");
  else
    printf("Flag submitted but not accepted - maybe you have already solved this phase?\n");
}

int main() {
  printf("Please enter your picoCTF account username, for automatic flag\n");
  printf("submission.\n");
  read_username();
  printf("Welcome to my fiendish little bomb. You have 6 phases with\n");
  printf("which to blow yourself up. Have a nice day!\n");
  char *input = read_line();
  phase_1(input);
  phase_defused();
  printf("Phase 1 defused. How about the next one?\n");
  input = read_line();
  phase_2(input);
  phase_defused();
  printf("That's number 2. Keep going!\n");
  input = read_line();
  phase_3(input);
  phase_defused();
  printf("Halfway there!\n");
  input = read_line();
  phase_4(input);
  phase_defused();
  printf("So you got that one. Try this one.\n");
  input = read_line();
  phase_5(input);
  phase_defused();
  printf("Good work! On to the next...\n");
  input = read_line();
  phase_6(input);
  phase_defused();
}
