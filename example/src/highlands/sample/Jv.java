package highlands.sample;

@org.immutables.value.Value.Immutable
interface X {
	int a();
}

public class Jv {
	public static void main(String... args) {
		System.out.println("Hello World!" + com.google.common.collect.ImmutableList.of());
		ImmutableX.builder().a(1).build();
	}
}
