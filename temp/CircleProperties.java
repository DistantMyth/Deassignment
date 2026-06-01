import java.util.Scanner;

public class CircleProperties {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        System.out.print("Enter radius: ");
        double radius = sc.nextDouble();

        double area = Math.PI * radius * radius;
        double circumference = 2 * Math.PI * radius;

        System.out.println("Area: " + area);
        System.out.println("Circumference: " + circumference);
        sc.close();
    }
}