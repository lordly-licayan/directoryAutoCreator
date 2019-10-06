package <packageName>;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.text.SimpleDateFormat;
import java.util.Date;


public class Test<ClassName> extends TestSQLInjection {
	public Test<ClassName>() {
		super();
	}

	public static void main(String[] args) throws Throwable {
		Test<ClassName> klaz = new Test<ClassName>();
	}

	@Override
	protected void beforeQuery(Object... args) throws SQLException {

	}

	@Override
	protected void afterQuery(Object... args) throws SQLException {

	}
}
