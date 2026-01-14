1+1;
defunc add(a: num, b: num) %num {
	ret a + b;
}

defunc greet(name: str) {
	!("Hello, ");
	!!(name);
}

x := 10;
y := 20;
sum := add(x, y);
!("Sum is: ");
!!(sum);
for(i, 0; i < 5; 1) {
	!("Loop iteration: ");
	!!(i);
}
if (1 < 2) {
	greet("World");
} else {
	greet("no");
}